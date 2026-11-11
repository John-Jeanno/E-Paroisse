from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver

from .storage import private_document_storage


def validate_parish_document_size(upload):
    max_size = 25 * 1024 * 1024
    if upload.size > max_size:
        raise ValidationError('Le fichier ne peut pas dépasser 25 Mo.')


def validate_announcement_media_size(upload):
    max_size = 100 * 1024 * 1024
    if upload.size > max_size:
        raise ValidationError('Le fichier média ne peut pas dépasser 100 Mo.')


validate_announcement_video_size = validate_announcement_media_size


class NotificationGroup(models.Model):
    name = models.CharField(_('nom du groupe'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('entité paroissiale')
        verbose_name_plural = _('entités paroissiales')

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('compte utilisateur'))
    phone_number = models.CharField(_('numéro de téléphone'), max_length=20, unique=True)
    first_name = models.CharField(_('prénom'), max_length=100)
    last_name = models.CharField(_('nom'), max_length=100)
    group = models.ForeignKey(NotificationGroup, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('groupe paroissial'))
    parish_entities = models.ManyToManyField(
        NotificationGroup,
        blank=True,
        related_name='members',
        verbose_name=_('entités paroissiales'),
    )
    otp_verified = models.BooleanField(_('téléphone vérifié'), default=False)

    class Meta:
        verbose_name = _('profil paroissial')
        verbose_name_plural = _('profils paroissiaux')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"


class IdempotencyRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_idempotency_records')
    key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField()
    response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'key'], name='unique_user_idempotency_key'),
        ]
        indexes = [
            models.Index(fields=['created_at']),
        ]


class OTPRequest(models.Model):
    PURPOSE_CHOICES = [
        ('registration', 'Inscription'),
        ('password_reset', 'Réinitialisation du mot de passe'),
    ]
    phone_number = models.CharField(_('numéro de téléphone'), max_length=20)
    code = models.CharField(_('code de vérification'), max_length=6)
    purpose = models.CharField(_('motif'), max_length=20, choices=PURPOSE_CHOICES, default='registration')
    created_at = models.DateTimeField(_('créée le'), auto_now_add=True)
    used = models.BooleanField(_('utilisée'), default=False)

    class Meta:
        verbose_name = _('demande de code de vérification')
        verbose_name_plural = _('demandes de codes de vérification')
        indexes = [
            models.Index(fields=['phone_number', 'code']),
        ]

    def __str__(self):
        return f"Code de vérification {self.code} pour {self.phone_number}"

    @staticmethod
    def generate_code():
        from secrets import randbelow
        return f"{randbelow(900000) + 100000:06d}"

class Announcement(models.Model):
    ANNOUNCEMENT_TYPES = [
        ('ban_mariage', 'Ban de mariage'),
        ('deces', 'Avis de décès'),
        ('communique', 'Communiqué'),
    ]
    title = models.CharField(_('titre'), max_length=255)
    body = models.TextField(_('contenu'))
    announcement_type = models.CharField(_('type d’annonce'), max_length=50, choices=ANNOUNCEMENT_TYPES)
    link_url = models.URLField(
        _('adresse du lien'),
        blank=True,
        default='',
        help_text=_('Lien externe affiché sous forme d’aperçu cliquable.'),
    )
    link_title = models.CharField(
        _('titre de l’aperçu du lien'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Titre affiché dans l’aperçu. À défaut, le domaine du lien est utilisé.'),
    )
    image_url = models.URLField(_('adresse de l’image'), blank=True, default='')
    video_url = models.URLField(_('adresse de la vidéo'), blank=True, default='')
    media_file = models.FileField(
        _('fichier média'),
        upload_to='announcements/media/%Y/%m/',
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4', 'm4v', 'mov', 'webm', 'jpg', 'jpeg', 'png']),
            validate_announcement_media_size,
        ],
        help_text=_('Formats acceptés : MP4, M4V, MOV, WebM, JPG, JPEG et PNG. Taille maximale : 100 Mo.'),
    )
    created_at = models.DateTimeField(_('créée le'), auto_now_add=True)
    published_at = models.DateTimeField(_('publiée le'), null=True, blank=True)
    target_groups = models.ManyToManyField(NotificationGroup, blank=True, verbose_name=_('groupes destinataires'))

    class Meta:
        verbose_name = _('annonce')
        verbose_name_plural = _('annonces')

    def __str__(self):
        return self.title


class AnnouncementComment(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('annonce'),
    )
    author = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='announcement_comments',
        verbose_name=_('auteur'),
    )
    body = models.TextField(_('commentaire'), max_length=2000)
    created_at = models.DateTimeField(_('publié le'), auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('commentaire d’annonce')
        verbose_name_plural = _('commentaires des annonces')

    def __str__(self):
        return f'{self.author} — {self.announcement.title}'


class AnnouncementLike(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name=_('annonce'),
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='announcement_likes',
        verbose_name=_('paroissien'),
    )
    created_at = models.DateTimeField(_('aimée le'), auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['announcement', 'user_profile'],
                name='unique_announcement_like_per_profile',
            ),
        ]
        verbose_name = _('mention J’aime')
        verbose_name_plural = _('mentions J’aime')

    def __str__(self):
        return f'{self.user_profile} aime {self.announcement.title}'


class AnnouncementShare(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='shares',
        verbose_name=_('annonce'),
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='announcement_shares',
        verbose_name=_('paroissien'),
    )
    created_at = models.DateTimeField(_('partagée le'), auto_now_add=True)

    class Meta:
        verbose_name = _('partage d’annonce')
        verbose_name_plural = _('partages des annonces')

    def __str__(self):
        return f'{self.user_profile} partage {self.announcement.title}'


class LiturgicalReading(models.Model):
    date = models.DateField(_('date'), unique=True)
    title = models.CharField(_('titre'), max_length=255)
    content = models.TextField(_('contenu'))
    source = models.CharField(_('source'), max_length=255, blank=True)

    class Meta:
        verbose_name = _('lecture liturgique')
        verbose_name_plural = _('lectures liturgiques')

    def __str__(self):
        return f"{self.date} - {self.title}"


class MassSchedule(models.Model):
    WEEKDAYS = [
        (0, _('Lundi')),
        (1, _('Mardi')),
        (2, _('Mercredi')),
        (3, _('Jeudi')),
        (4, _('Vendredi')),
        (5, _('Samedi')),
        (6, _('Dimanche')),
    ]

    weekday = models.PositiveSmallIntegerField(_('jour de la semaine'), choices=WEEKDAYS, null=True, blank=True)
    date = models.DateField(_('date ponctuelle'), null=True, blank=True)
    time = models.TimeField(_('heure'))
    location = models.CharField(_('lieu'), max_length=200)
    active = models.BooleanField(_('actif'), default=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)

    class Meta:
        ordering = ['date', 'weekday', 'time']
        verbose_name = _('horaire de messe')
        verbose_name_plural = _('horaires de messe')

    def clean(self):
        super().clean()
        if (self.weekday is None) == (self.date is None):
            raise ValidationError(_('Choisissez soit un jour récurrent, soit une date ponctuelle.'))

    def __str__(self):
        when = self.date or self.get_weekday_display()
        return f'{when} — {self.time:%H:%M} — {self.location}'


class DonationSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    wave_identifier = models.CharField(_('identifiant marchand Wave'), max_length=100, blank=True)
    orange_money_identifier = models.CharField(_('identifiant marchand Orange Money'), max_length=100, blank=True)
    parish_contact_phone = models.CharField(
        _('numéro de contact paroissial'),
        max_length=30,
        default='77 123 45 67',
    )
    instructions = models.TextField(_('instructions de don'), blank=True)

    class Meta:
        verbose_name = _('configuration des dons')
        verbose_name_plural = _('configuration des dons')

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return str(_('Configuration des dons'))


class MassRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('declined', 'Refusée'),
    ]

    requester = models.ForeignKey(UserProfile, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('demandeur'))
    phone = models.CharField(_('téléphone de contact'), max_length=20, blank=True)
    contact_email = models.EmailField(_('adresse e-mail'), blank=True)
    locality = models.CharField(_('ville et quartier de résidence'), max_length=200, blank=True)
    preferred_date = models.DateTimeField(_('date souhaitée'), null=True, blank=True)
    message = models.TextField(_('intention de messe'))
    status = models.CharField(_('état'), max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(_('reçue le'), auto_now_add=True)

    class Meta:
        verbose_name = _('demande de messe')
        verbose_name_plural = _('demandes de messe')

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()
        update_fields = kwargs.get('update_fields')
        super().save(*args, **kwargs)

        if (
            previous_status is not None
            and previous_status != self.status
            and (update_fields is None or 'status' in update_fields)
            and self.requester_id
        ):
            ParishNotification.objects.create(
                recipient_id=self.requester_id,
                mass_request=self,
                kind='mass_request_status',
                title='Réponse à votre demande de messe',
                message=f'Votre demande de messe a été {self.get_status_display().lower()}.',
            )

    def __str__(self):
        who = self.requester.first_name + ' ' + self.requester.last_name if self.requester else (self.phone or 'Anonyme')
        return f"Demande de messe de {who} - {self.preferred_date or 'à déterminer'}"


class ParishNotification(models.Model):
    KIND_CHOICES = [
        ('mass_request_status', 'Réponse à une demande de messe'),
    ]

    recipient = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='parish_notifications',
        verbose_name=_('destinataire'),
    )
    mass_request = models.ForeignKey(
        MassRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications',
        verbose_name=_('demande de messe'),
    )
    kind = models.CharField(_('type'), max_length=32, choices=KIND_CHOICES)
    title = models.CharField(_('titre'), max_length=200)
    message = models.TextField(_('message'))
    is_read = models.BooleanField(_('lue'), default=False)
    created_at = models.DateTimeField(_('créée le'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('notification paroissiale')
        verbose_name_plural = _('notifications paroissiales')

    def __str__(self):
        return f'{self.title} — {self.recipient}'


class PrivateMessage(models.Model):
    sender = models.ForeignKey(UserProfile, related_name='sent_messages', on_delete=models.CASCADE, verbose_name=_('expéditeur'))
    recipient = models.ForeignKey(UserProfile, related_name='received_messages', on_delete=models.CASCADE, verbose_name=_('destinataire'))
    body = models.TextField(_('message'), max_length=2000, blank=True)
    audio = models.FileField(_('message vocal'), upload_to='messages/private/%Y/%m/', blank=True, null=True)
    is_read = models.BooleanField(_('lu'), default=False)
    created_at = models.DateTimeField(_('envoyé le'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('message privé')
        verbose_name_plural = _('messages privés')

    def __str__(self):
        return f'Message de {self.sender} à {self.recipient}'


class ParishGroupMessage(models.Model):
    entity = models.ForeignKey(
        NotificationGroup,
        related_name='messages',
        on_delete=models.CASCADE,
        verbose_name=_('entité paroissiale'),
    )
    sender = models.ForeignKey(
        UserProfile,
        related_name='sent_parish_messages',
        on_delete=models.CASCADE,
        verbose_name=_('expéditeur'),
    )
    body = models.TextField(_('message'), max_length=2000, blank=True)
    audio = models.FileField(_('message vocal'), upload_to='messages/parish/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(_('envoyé le'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('message d’entité paroissiale')
        verbose_name_plural = _('messages d’entités paroissiales')

    def __str__(self):
        return f'Message de {self.sender} dans {self.entity}'


class ParishGroupReadState(models.Model):
    profile = models.ForeignKey(
        UserProfile,
        related_name='parish_group_read_states',
        on_delete=models.CASCADE,
        verbose_name=_('paroissien'),
    )
    entity = models.ForeignKey(
        NotificationGroup,
        related_name='member_read_states',
        on_delete=models.CASCADE,
        verbose_name=_('entité paroissiale'),
    )
    last_read_at = models.DateTimeField(_('dernière lecture'), default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['profile', 'entity'], name='unique_parish_group_read_state'),
        ]
        verbose_name = _('état de lecture des messages d’entité')
        verbose_name_plural = _('états de lecture des messages d’entités')


@receiver(m2m_changed, sender=UserProfile.parish_entities.through)
def create_parish_group_read_states(sender, instance, action, reverse, pk_set, **kwargs):
    if action != 'post_add' or not pk_set:
        return
    profiles = (
        UserProfile.objects.filter(pk__in=pk_set)
        if reverse
        else [instance]
    )
    entity_ids = [instance.pk] if reverse else pk_set
    ParishGroupReadState.objects.bulk_create(
        [
            ParishGroupReadState(profile=profile, entity_id=entity_id)
            for profile in profiles
            for entity_id in entity_ids
        ],
        ignore_conflicts=True,
    )


class ParishDocument(models.Model):
    CATEGORY_CHOICES = [
        ('administrative', 'Administration et courriers'),
        ('finance', 'Finances'),
        ('sacraments', 'Registres sacramentels'),
        ('pastoral', 'Pastorale et activités'),
        ('personnel', 'Personnel et bénévolat'),
        ('other', 'Autre'),
    ]
    DOCUMENT_TYPE_CHOICES = [
        ('letter', 'Courrier'),
        ('certificate', 'Attestation ou certificat'),
        ('minutes', 'Compte rendu / procès-verbal'),
        ('sacramental_record', 'Acte ou extrait sacramentel'),
        ('announcement', 'Annonce ou note'),
        ('form', 'Formulaire ou fiche de suivi'),
        ('other', 'Autre document'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('review', 'À valider'),
        ('approved', 'Validé'),
        ('archived', 'Archivé'),
    ]
    CONFIDENTIALITY_CHOICES = [
        ('internal', 'Interne'),
        ('restricted', 'Confidentiel'),
    ]
    SENSITIVE_CATEGORIES = ('finance', 'sacraments', 'personnel')
    SENSITIVE_DOCUMENT_TYPES = ('sacramental_record',)

    title = models.CharField(_('titre'), max_length=255)
    category = models.CharField(_('catégorie'), max_length=30, choices=CATEGORY_CHOICES)
    document_type = models.CharField(_('type de document'), max_length=30, choices=DOCUMENT_TYPE_CHOICES, default='other')
    document_date = models.DateField(_('date du document'), default=timezone.localdate)
    reference_number = models.CharField(_('numéro de référence'), max_length=100, blank=True)
    description = models.TextField(_('description'), blank=True)
    template = models.ForeignKey(
        'ParishDocumentTemplate',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='documents',
        verbose_name=_('modèle utilisé'),
    )
    content = models.TextField(
        _('contenu du document'),
        blank=True,
        help_text=_('Texte du document à produire dans Word. Les retours à la ligne sont conservés.'),
    )
    attachment = models.FileField(
        _('fichier à archiver'),
        upload_to='records/%Y/%m/',
        storage=private_document_storage,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'odt', 'xls', 'xlsx', 'csv', 'jpg', 'jpeg', 'png']
            ),
            validate_parish_document_size,
        ],
        help_text=_('Fichier privé, limité à 25 Mo. Formats acceptés : PDF, Word, tableur, CSV et image.'),
    )
    confidentiality = models.CharField(_('niveau de confidentialité'), max_length=20, choices=CONFIDENTIALITY_CHOICES, default='internal')
    status = models.CharField(_('état du workflow'), max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='parish_documents_created',
        verbose_name=_('créé par'),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='parish_documents_to_review',
        verbose_name=_('validateur désigné'),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='parish_documents_approved',
        verbose_name=_('validé par'),
    )
    approved_at = models.DateTimeField(_('validé le'), null=True, blank=True)
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modifié le'), auto_now=True)

    class Meta:
        ordering = ['-document_date', '-created_at']
        verbose_name = _('document paroissial')
        verbose_name_plural = _('documents paroissiaux')
        permissions = [
            ('view_sensitive_parishdocument', _('Peut consulter les documents paroissiaux confidentiels')),
            ('approve_parishdocument', _('Peut valider et archiver les documents paroissiaux')),
        ]

    @property
    def is_confidential(self):
        return (
            self.category in self.SENSITIVE_CATEGORIES
            or self.document_type in self.SENSITIVE_DOCUMENT_TYPES
            or self.confidentiality == 'restricted'
        )

    def save(self, *args, **kwargs):
        if (
            self.category in self.SENSITIVE_CATEGORIES
            or self.document_type in self.SENSITIVE_DOCUMENT_TYPES
        ):
            self.confidentiality = 'restricted'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} ({self.document_date:%Y-%m-%d})'


class ParishDocumentWorkflowEvent(models.Model):
    ACTION_CHOICES = [
        ('created', 'Créé'),
        ('submitted', 'Soumis à validation'),
        ('approved', 'Validé'),
        ('archived', 'Archivé'),
        ('returned', 'Renvoyé en brouillon'),
        ('revised', 'Modifié — validation réinitialisée'),
    ]

    document = models.ForeignKey(ParishDocument, on_delete=models.CASCADE, related_name='workflow_events', verbose_name=_('document'))
    action = models.CharField(_('action effectuée'), max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('effectuée par'))
    note = models.CharField(_('commentaire'), max_length=255, blank=True)
    created_at = models.DateTimeField(_('date de l’action'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('étape du circuit de validation')
        verbose_name_plural = _('historique du circuit de validation')

    def __str__(self):
        return f'{self.get_action_display()} — {self.document.title}'


class ParishDocumentTemplate(models.Model):
    name = models.CharField(_('nom du modèle'), max_length=150, unique=True)
    category = models.CharField(_('catégorie'), max_length=30, choices=ParishDocument.CATEGORY_CHOICES)
    document_type = models.CharField(_('type de document'), max_length=30, choices=ParishDocument.DOCUMENT_TYPE_CHOICES)
    title_template = models.CharField(_('titre prérempli'), max_length=255)
    content_template = models.TextField(
        _('contenu prérempli'),
        help_text=_('Modèle de texte. Les noms, dates et autres informations sont complétés dans le document créé.')
    )
    is_active = models.BooleanField(_('modèle actif'), default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='parish_document_templates_created',
        verbose_name=_('créé par'),
    )
    created_at = models.DateTimeField(_('créé le'), auto_now_add=True)
    updated_at = models.DateTimeField(_('modifié le'), auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('modèle de document paroissial')
        verbose_name_plural = _('modèles de documents paroissiaux')

    @property
    def is_confidential(self):
        return (
            self.category in ParishDocument.SENSITIVE_CATEGORIES
            or self.document_type in ParishDocument.SENSITIVE_DOCUMENT_TYPES
        )

    def __str__(self):
        return self.name


class QuizQuestion(models.Model):
    TESTAMENT_CHOICES = [
        ('ancien', 'Ancien Testament'),
        ('nouveau', 'Nouveau Testament'),
    ]

    testament = models.CharField(_('testament'), max_length=10, choices=TESTAMENT_CHOICES)
    category = models.CharField(_('catégorie'), max_length=100)
    prompt = models.CharField(_('question'), max_length=500)
    options = models.JSONField(_('choix de réponse'))
    correct_option = models.PositiveSmallIntegerField(_('bonne réponse'))
    explanation = models.CharField(_('explication'), max_length=500)
    is_active = models.BooleanField(_('active'), default=True)

    class Meta:
        ordering = ['id']
        verbose_name = _('question biblique')
        verbose_name_plural = _('questions bibliques')

    def clean(self):
        super().clean()
        if (
            not isinstance(self.options, list)
            or len(self.options) != 3
            or any(not isinstance(option, str) or not option.strip() for option in self.options)
        ):
            raise ValidationError({'options': 'Une question doit proposer exactement trois choix non vides.'})
        if self.correct_option not in range(3):
            raise ValidationError({'correct_option': 'La bonne réponse doit correspondre à l’un des trois choix.'})

    def __str__(self):
        return self.prompt


class OfflineQuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offline_quiz_results')
    client_session_id = models.CharField(max_length=64)
    answers = models.JSONField()
    correct_count = models.PositiveSmallIntegerField(default=0)
    total_questions = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'client_session_id'],
                name='unique_user_offline_quiz_session',
            ),
        ]
        ordering = ['-created_at']


class QuizSession(models.Model):
    MODE_CHOICES = [('text', 'Texte'), ('audio', 'Audio')]
    STATUS_CHOICES = [
        ('active', 'En cours'),
        ('paused', 'En pause'),
        ('completed', 'Terminée'),
    ]

    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='quiz_sessions')
    mode = models.CharField(_('mode'), max_length=10, choices=MODE_CHOICES)
    timer_waits_for_audio = models.BooleanField(default=False)
    status = models.CharField(_('état'), max_length=10, choices=STATUS_CHOICES, default='active')
    current_index = models.PositiveSmallIntegerField(_('question actuelle'), default=0)
    created_at = models.DateTimeField(_('créée le'), auto_now_add=True)
    completed_at = models.DateTimeField(_('terminée le'), null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('partie individuelle')
        verbose_name_plural = _('parties individuelles')

    def __str__(self):
        return f'Partie de {self.profile} ({self.get_mode_display()})'


class QuizSessionQuestion(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='session_questions')
    question = models.ForeignKey(QuizQuestion, on_delete=models.PROTECT, related_name='session_questions')
    position = models.PositiveSmallIntegerField()
    remaining_seconds = models.PositiveSmallIntegerField(default=40)
    timer_started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['session', 'position'], name='unique_quiz_session_position'),
            models.UniqueConstraint(fields=['session', 'question'], name='unique_quiz_session_question'),
        ]


class QuizSessionResponse(models.Model):
    session_question = models.OneToOneField(
        QuizSessionQuestion, on_delete=models.CASCADE, related_name='response'
    )
    option_index = models.PositiveSmallIntegerField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    timed_out = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)


class QuizChallenge(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('active', 'En cours'),
        ('declined', 'Refusée'),
        ('completed', 'Terminée'),
        ('expired', 'Expirée'),
    ]

    challenger = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='quiz_challenges_sent')
    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='quiz_challenges_received')
    status = models.CharField(_('état'), max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(_('créée le'), auto_now_add=True)
    accepted_at = models.DateTimeField(_('acceptée le'), null=True, blank=True)
    completed_at = models.DateTimeField(_('terminée le'), null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=~models.Q(challenger=models.F('recipient')), name='quiz_challenge_not_self'),
        ]
        verbose_name = _('défi biblique')
        verbose_name_plural = _('défis bibliques')

    def __str__(self):
        return f'Défi de {self.challenger} à {self.recipient}'


class QuizChallengeNotification(models.Model):
    KIND_CHOICES = [
        ('invitation', 'Invitation reçue'),
        ('accepted', 'Défi accepté'),
        ('declined', 'Défi refusé'),
    ]

    recipient = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='quiz_notifications',
    )
    challenge = models.ForeignKey(
        QuizChallenge,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='quiz_notifications_sent',
    )
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['recipient', 'challenge', 'kind'],
                name='unique_quiz_notification_event',
            ),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} — {self.recipient}'


class QuizChallengeQuestion(models.Model):
    challenge = models.ForeignKey(QuizChallenge, on_delete=models.CASCADE, related_name='challenge_questions')
    question = models.ForeignKey(QuizQuestion, on_delete=models.PROTECT, related_name='challenge_questions')
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['challenge', 'position'], name='unique_quiz_challenge_position'),
            models.UniqueConstraint(fields=['challenge', 'question'], name='unique_quiz_challenge_question'),
        ]


class QuizChallengeParticipant(models.Model):
    challenge = models.ForeignKey(QuizChallenge, on_delete=models.CASCADE, related_name='participants')
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='quiz_challenge_participations')
    current_index = models.PositiveSmallIntegerField(default=0)
    remaining_seconds = models.PositiveSmallIntegerField(default=90)
    timer_started_at = models.DateTimeField(null=True, blank=True)
    is_paused = models.BooleanField(default=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    timed_out = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['challenge', 'profile'], name='unique_quiz_challenge_participant'),
        ]


class QuizChallengeResponse(models.Model):
    participant = models.ForeignKey(
        QuizChallengeParticipant, on_delete=models.CASCADE, related_name='responses'
    )
    challenge_question = models.ForeignKey(
        QuizChallengeQuestion, on_delete=models.CASCADE, related_name='responses'
    )
    option_index = models.PositiveSmallIntegerField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    timed_out = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['participant', 'challenge_question'], name='unique_quiz_challenge_response'
            ),
        ]
