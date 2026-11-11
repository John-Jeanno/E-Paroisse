from io import BytesIO
from pathlib import Path

from docx import Document
from django.contrib import admin
from django.contrib import messages
from django import forms
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import path, reverse
from django.utils.http import urlencode
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from .models import (
    Announcement,
    AnnouncementComment,
    LiturgicalReading,
    MassSchedule,
    DonationSettings,
    MassRequest,
    NotificationGroup,
    ParishGroupMessage,
    OTPRequest,
    ParishDocument,
    ParishDocumentTemplate,
    ParishDocumentWorkflowEvent,
    PrivateMessage,
    QuizChallenge,
    QuizChallengeNotification,
    QuizChallengeQuestion,
    QuizChallengeResponse,
    QuizQuestion,
    QuizSession,
    QuizSessionQuestion,
    QuizSessionResponse,
    UserProfile,
)

admin.site.site_header = _('Paroisse NDA Ouakam')
admin.site.site_title = _('Paroisse NDA Ouakam')
admin.site.index_title = _('Gestion paroissiale')


class MassScheduleAdminForm(forms.ModelForm):
    class Meta:
        model = MassSchedule
        fields = '__all__'
        help_texts = {
            'weekday': _('Pour un horaire récurrent chaque semaine, choisissez un jour et laissez la date ponctuelle vide.'),
            'date': _('Pour une seule date, laissez le jour de la semaine vide.'),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('weekday') is not None and cleaned_data.get('date') is not None:
            self.add_error(
                'date',
                _('Pour un horaire récurrent, effacez la date ponctuelle. Pour une messe à une date précise, laissez le jour vide.'),
            )
        return cleaned_data


class AnnouncementCommentInline(admin.TabularInline):
    model = AnnouncementComment
    extra = 0
    can_delete = True
    fields = ('created_at', 'author', 'body')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'first_name', 'last_name', 'group')
    search_fields = ('phone_number', 'first_name', 'last_name', 'group__name')
    list_filter = ('group', 'otp_verified')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'announcement_type', 'media_preview', 'published_at')
    list_filter = ('announcement_type', 'published_at')
    search_fields = ('title', 'body', 'link_title', 'link_url')
    actions = ('publish_selected', 'unpublish_selected')
    inlines = (AnnouncementCommentInline,)

    @admin.display(description='Média')
    def media_preview(self, obj):
        if obj.media_file:
            return 'Vidéo' if obj.media_file.name.lower().endswith(('.mp4', '.m4v', '.mov', '.webm')) else 'Image'
        if obj.video_url:
            return 'Vidéo'
        if obj.image_url:
            return 'Image'
        if obj.link_url:
            return 'Lien'
        return 'Aucun média'

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'media_file' and formfield:
            formfield.widget.attrs['accept'] = '.mp4,.m4v,.mov,.webm,.jpg,.jpeg,.png'
        return formfield

    @admin.action(description="Publier les annonces sélectionnées")
    def publish_selected(self, request, queryset):
        updated = queryset.update(published_at=timezone.now())
        self.message_user(request, f"{updated} annonce(s) publiée(s).")

    @admin.action(description="Retirer les annonces sélectionnées")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(published_at=None)
        self.message_user(request, f"{updated} annonce(s) retirée(s) de la publication.")


@admin.register(AnnouncementComment)
class AnnouncementCommentAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'author', 'comment_preview', 'created_at')
    list_filter = ('created_at', 'announcement__announcement_type')
    search_fields = ('announcement__title', 'author__first_name', 'author__last_name', 'author__phone_number', 'body')
    readonly_fields = ('announcement', 'author', 'body', 'created_at')

    @admin.display(description='Commentaire')
    def comment_preview(self, obj):
        return Truncator(obj.body).chars(100)

    def has_add_permission(self, request):
        return False


class QuizSessionQuestionInline(admin.TabularInline):
    model = QuizSessionQuestion
    extra = 0
    readonly_fields = ('position', 'question', 'remaining_seconds', 'timer_started_at')
    can_delete = False


class QuizChallengeQuestionInline(admin.TabularInline):
    model = QuizChallengeQuestion
    extra = 0
    readonly_fields = ('position', 'question')
    can_delete = False


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('prompt', 'testament', 'category', 'is_active')
    list_filter = ('testament', 'category', 'is_active')
    search_fields = ('prompt', 'explanation')


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'mode', 'status', 'current_index', 'created_at')
    list_filter = ('mode', 'status', 'created_at')
    search_fields = ('profile__first_name', 'profile__last_name', 'profile__phone_number')
    readonly_fields = ('profile', 'mode', 'status', 'current_index', 'created_at', 'completed_at')
    inlines = (QuizSessionQuestionInline,)


@admin.register(QuizChallenge)
class QuizChallengeAdmin(admin.ModelAdmin):
    list_display = ('id', 'challenger', 'recipient', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('challenger__first_name', 'challenger__last_name', 'recipient__first_name', 'recipient__last_name')
    readonly_fields = ('challenger', 'recipient', 'status', 'created_at', 'accepted_at', 'completed_at')
    inlines = (QuizChallengeQuestionInline,)


@admin.register(QuizChallengeNotification)
class QuizChallengeNotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'kind', 'challenge', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read', 'created_at')
    search_fields = (
        'recipient__first_name',
        'recipient__last_name',
        'actor__first_name',
        'actor__last_name',
    )
    readonly_fields = ('recipient', 'actor', 'kind', 'challenge', 'created_at')


@admin.register(QuizSessionResponse)
class QuizSessionResponseAdmin(admin.ModelAdmin):
    list_display = ('session_question', 'option_index', 'is_correct', 'timed_out', 'answered_at')
    readonly_fields = ('session_question', 'option_index', 'is_correct', 'timed_out', 'answered_at')


@admin.register(QuizChallengeResponse)
class QuizChallengeResponseAdmin(admin.ModelAdmin):
    list_display = ('participant', 'challenge_question', 'option_index', 'is_correct', 'timed_out', 'answered_at')
    readonly_fields = ('participant', 'challenge_question', 'option_index', 'is_correct', 'timed_out', 'answered_at')

    def get_readonly_fields(self, request, obj=None):
        return ('announcement', 'author', 'body', 'created_at')


@admin.register(LiturgicalReading)
class LiturgicalReadingAdmin(admin.ModelAdmin):
    list_display = ('date', 'title')
    list_filter = ('date',)


@admin.register(MassSchedule)
class MassScheduleAdmin(admin.ModelAdmin):
    form = MassScheduleAdminForm
    list_display = ('weekday', 'date', 'time', 'location', 'active')
    list_filter = ('active', 'weekday', 'date')
    search_fields = ('location',)
    ordering = ('date', 'weekday', 'time')


@admin.register(DonationSettings)
class DonationSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('parish_contact_phone', 'wave_identifier', 'orange_money_identifier', 'instructions')}),
    )

    def has_add_permission(self, request):
        return not DonationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'purpose', 'code', 'created_at', 'used')
    list_filter = ('purpose', 'used', 'created_at')
    search_fields = ('phone_number',)
    readonly_fields = ('phone_number', 'code', 'created_at', 'used')

@admin.register(NotificationGroup)
class NotificationGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = (Lower('name'), 'name')


@admin.register(ParishGroupMessage)
class ParishGroupMessageAdmin(admin.ModelAdmin):
    list_display = ('entity', 'sender', 'created_at')
    list_filter = ('entity', 'created_at')
    search_fields = ('entity__name', 'sender__first_name', 'sender__last_name', 'body')
    readonly_fields = ('entity', 'sender', 'body', 'created_at')


@admin.register(MassRequest)
class MassRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'phone', 'locality', 'contact_email', 'preferred_date', 'message_preview', 'status', 'created_at')
    list_filter = ('status', 'preferred_date', 'created_at')
    search_fields = (
        'phone',
        'contact_email',
        'locality',
        'message',
        'requester__first_name',
        'requester__last_name',
        'requester__phone_number',
    )
    list_select_related = ('requester', 'requester__user')
    actions = ('accept_selected', 'decline_selected')

    @admin.display(description="Motif")
    def message_preview(self, obj):
        return Truncator(obj.message).chars(80)

    @admin.action(description="Accepter les demandes sélectionnées")
    def accept_selected(self, request, queryset):
        updated = 0
        for mass_request in queryset.iterator():
            mass_request.status = 'accepted'
            mass_request.save(update_fields=['status'])
            updated += 1
        self.message_user(request, f"{updated} demande(s) de messe acceptée(s).")

    @admin.action(description="Refuser les demandes sélectionnées")
    def decline_selected(self, request, queryset):
        updated = 0
        for mass_request in queryset.iterator():
            mass_request.status = 'declined'
            mass_request.save(update_fields=['status'])
            updated += 1
        self.message_user(request, f"{updated} demande(s) de messe refusée(s).")


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__first_name', 'sender__last_name', 'recipient__first_name', 'recipient__last_name', 'body')


class ParishDocumentWorkflowEventInline(admin.TabularInline):
    model = ParishDocumentWorkflowEvent
    extra = 0
    can_delete = False
    fields = ('created_at', 'action', 'actor', 'note')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return False
        if not (
            request.user.has_perm('api.view_parishdocument')
            or request.user.has_perm('api.change_parishdocument')
        ):
            return False
        if obj.is_confidential and not request.user.has_perm('api.view_sensitive_parishdocument'):
            return False
        if not request.user.has_perm('api.view_parishdocument'):
            return request.user.has_perm('api.change_parishdocument')
        return True


@admin.register(ParishDocument)
class ParishDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'document_type',
        'document_date',
        'reference_number',
        'status',
        'confidentiality',
        'reviewer',
    )
    list_filter = ('category', 'document_type', 'status', 'confidentiality', 'document_date')
    search_fields = ('title', 'reference_number', 'description', 'content')
    list_select_related = ('created_by', 'reviewer', 'approved_by')
    date_hierarchy = 'document_date'
    readonly_fields = ('status', 'created_by', 'created_at', 'updated_at', 'approved_by', 'approved_at', 'word_download')
    inlines = (ParishDocumentWorkflowEventInline,)
    actions = ('submit_for_review', 'approve_documents', 'return_to_draft', 'archive_documents')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.has_perm('api.view_sensitive_parishdocument'):
            queryset = queryset.exclude(
                Q(category__in=ParishDocument.SENSITIVE_CATEGORIES)
                | Q(document_type__in=ParishDocument.SENSITIVE_DOCUMENT_TYPES)
                | Q(confidentiality='restricted')
            )
        return queryset

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        if obj and obj.is_confidential:
            return request.user.has_perm('api.view_sensitive_parishdocument')
        return True

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj and obj.is_confidential:
            return request.user.has_perm('api.view_sensitive_parishdocument')
        return True

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj and obj.is_confidential:
            return request.user.has_perm('api.view_sensitive_parishdocument')
        return True

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if not request.user.has_perm('api.view_sensitive_parishdocument'):
            if db_field.name == 'category':
                kwargs['choices'] = [
                    choice for choice in ParishDocument.CATEGORY_CHOICES
                    if choice[0] not in ParishDocument.SENSITIVE_CATEGORIES
                ]
            elif db_field.name == 'document_type':
                kwargs['choices'] = [
                    choice for choice in ParishDocument.DOCUMENT_TYPE_CHOICES
                    if choice[0] not in ParishDocument.SENSITIVE_DOCUMENT_TYPES
                ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.has_perm('api.view_sensitive_parishdocument'):
            readonly_fields.append('confidentiality')
        return readonly_fields

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        template_id = request.GET.get('template')
        if not template_id:
            return initial
        template = ParishDocumentTemplate.objects.filter(pk=template_id, is_active=True).first()
        if template is None:
            return initial
        if (
            template.is_confidential
            and not request.user.has_perm('api.view_sensitive_parishdocument')
        ):
            return initial
        initial.update({
            'template': template.pk,
            'title': template.title_template,
            'category': template.category,
            'document_type': template.document_type,
            'content': template.content_template,
        })
        return initial

    def get_urls(self):
        custom_urls = [
            path(
                'private-file/<path:filename>',
                self.admin_site.admin_view(self.download_attachment),
                name='api_parishdocument_download_attachment',
            ),
            path(
                '<path:object_id>/download-word/',
                self.admin_site.admin_view(self.download_word),
                name='api_parishdocument_download_word',
            ),
        ]
        return custom_urls + super().get_urls()

    def download_attachment(self, request, filename):
        if not (
            self.has_view_permission(request)
            or self.has_change_permission(request)
        ):
            return HttpResponseForbidden()
        document = self.get_queryset(request).filter(attachment=filename).first()
        if document is None or not document.attachment:
            raise Http404
        return FileResponse(
            document.attachment.open('rb'),
            as_attachment=True,
            filename=Path(document.attachment.name).name,
        )

    def download_word(self, request, object_id):
        document = self.get_queryset(request).filter(pk=object_id).first()
        if document is None:
            raise Http404
        if not self.has_view_permission(request, document):
            return HttpResponseForbidden()
        if not document.content.strip():
            raise Http404

        word_document = Document()
        word_document.add_heading(document.title, level=0)
        metadata = word_document.add_paragraph()
        metadata.add_run(
            f"{document.get_category_display()} — {document.document_date:%d/%m/%Y}"
        ).italic = True
        if document.reference_number:
            word_document.add_paragraph(f"Référence : {document.reference_number}")
        if document.description:
            word_document.add_paragraph(document.description)
        word_document.add_paragraph()
        for line in document.content.splitlines():
            word_document.add_paragraph(line)

        buffer = BytesIO()
        word_document.save(buffer)
        buffer.seek(0)
        filename = f"{slugify(document.title) or 'document-paroissial'}.docx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @admin.display(description='Télécharger le document Word')
    def word_download(self, obj):
        if obj is None or not obj.content.strip():
            return 'Saisissez un texte dans le champ « Contenu du document » pour générer le fichier Word.'
        url = reverse('admin:api_parishdocument_download_word', kwargs={'object_id': obj.pk})
        return format_html('<a href="{}">Télécharger le document .docx</a>', url)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'reviewer':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(is_staff=True).order_by('username')
        elif db_field.name == 'template' and not request.user.has_perm('api.view_sensitive_parishdocument'):
            kwargs['queryset'] = ParishDocumentTemplate.objects.exclude(
                category__in=ParishDocument.SENSITIVE_CATEGORIES
            ).exclude(
                document_type__in=ParishDocument.SENSITIVE_DOCUMENT_TYPES
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        original = None
        if change:
            original = ParishDocument.objects.get(pk=obj.pk)
        if not obj.created_by_id:
            obj.created_by = request.user
        content_changed = original is not None and any(
            getattr(original, field) != getattr(obj, field)
            for field in (
                'title',
                'category',
                'document_type',
                'document_date',
                'reference_number',
                'description',
                'template_id',
                'content',
                'confidentiality',
            )
        )
        if original and original.attachment.name != obj.attachment.name:
            content_changed = True
        if original and content_changed and original.status != 'draft':
            obj.status = 'draft'
            obj.approved_by = None
            obj.approved_at = None
        super().save_model(request, obj, form, change)
        if original is None:
            ParishDocumentWorkflowEvent.objects.create(
                document=obj,
                action='created',
                actor=request.user,
            )
        elif content_changed and original.status != 'draft':
            ParishDocumentWorkflowEvent.objects.create(
                document=obj,
                action='revised',
                actor=request.user,
                note='Le document a été modifié et doit être soumis de nouveau.',
            )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm('api.approve_parishdocument'):
            for action in ('approve_documents', 'return_to_draft', 'archive_documents'):
                actions.pop(action, None)
        return actions

    @admin.action(description='Soumettre les brouillons sélectionnés à validation')
    def submit_for_review(self, request, queryset):
        drafts = queryset.filter(status='draft')
        candidates = drafts.filter(Q(content__gt='') | Q(attachment__gt=''))
        documents = [document for document in candidates if document.content.strip() or document.attachment]
        skipped = drafts.count() - len(documents)
        for document in documents:
            document.status = 'review'
            document.save(update_fields=['status', 'updated_at'])
            ParishDocumentWorkflowEvent.objects.create(
                document=document,
                action='submitted',
                actor=request.user,
            )
        self.message_user(request, f'{len(documents)} document(s) soumis à validation.')
        if skipped:
            self.message_user(
                request,
                f'{skipped} brouillon(s) vide(s) ignoré(s) : ajoutez un texte ou un fichier avant la validation.',
                level=messages.WARNING,
            )

    @admin.action(description='Valider les documents sélectionnés')
    def approve_documents(self, request, queryset):
        if not request.user.has_perm('api.approve_parishdocument'):
            return HttpResponseForbidden()
        documents = queryset.filter(status='review')
        if not request.user.is_superuser:
            documents = documents.exclude(created_by=request.user)
        now = timezone.now()
        count = 0
        for document in documents:
            document.status = 'approved'
            document.approved_by = request.user
            document.approved_at = now
            document.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
            ParishDocumentWorkflowEvent.objects.create(
                document=document,
                action='approved',
                actor=request.user,
            )
            count += 1
        self.message_user(request, f'{count} document(s) validé(s).')

    @admin.action(description='Renvoyer les documents sélectionnés en brouillon')
    def return_to_draft(self, request, queryset):
        if not request.user.has_perm('api.approve_parishdocument'):
            return HttpResponseForbidden()
        documents = list(queryset.filter(status='review'))
        for document in documents:
            document.status = 'draft'
            document.save(update_fields=['status', 'updated_at'])
            ParishDocumentWorkflowEvent.objects.create(
                document=document,
                action='returned',
                actor=request.user,
            )
        self.message_user(request, f'{len(documents)} document(s) renvoyé(s) en brouillon.')

    @admin.action(description='Archiver les documents validés sélectionnés')
    def archive_documents(self, request, queryset):
        if not request.user.has_perm('api.approve_parishdocument'):
            return HttpResponseForbidden()
        documents = list(queryset.filter(status='approved'))
        for document in documents:
            document.status = 'archived'
            document.save(update_fields=['status', 'updated_at'])
            ParishDocumentWorkflowEvent.objects.create(
                document=document,
                action='archived',
                actor=request.user,
            )
        self.message_user(request, f'{len(documents)} document(s) archivé(s).')


@admin.register(ParishDocumentTemplate)
class ParishDocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'document_type', 'is_active', 'create_document_link')
    list_filter = ('category', 'document_type', 'is_active')
    search_fields = ('name', 'title_template', 'content_template')
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.has_perm('api.view_sensitive_parishdocument'):
            queryset = queryset.exclude(
                Q(category__in=ParishDocument.SENSITIVE_CATEGORIES)
                | Q(document_type__in=ParishDocument.SENSITIVE_DOCUMENT_TYPES)
            )
        return queryset

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        if obj and obj.is_confidential:
            return request.user.has_perm('api.view_sensitive_parishdocument')
        return True

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj and obj.is_confidential:
            return request.user.has_perm('api.view_sensitive_parishdocument')
        return True

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if (
            not request.user.has_perm('api.view_sensitive_parishdocument')
        ):
            if db_field.name == 'category':
                kwargs['choices'] = [
                    choice for choice in ParishDocument.CATEGORY_CHOICES
                    if choice[0] not in ParishDocument.SENSITIVE_CATEGORIES
                ]
            elif db_field.name == 'document_type':
                kwargs['choices'] = [
                    choice for choice in ParishDocument.DOCUMENT_TYPE_CHOICES
                    if choice[0] not in ParishDocument.SENSITIVE_DOCUMENT_TYPES
                ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        custom_urls = [
            path(
                '<int:object_id>/create-document/',
                self.admin_site.admin_view(self.create_document),
                name='api_parishdocumenttemplate_create_document',
            ),
        ]
        return custom_urls + super().get_urls()

    def create_document(self, request, object_id):
        template = self.get_queryset(request).filter(pk=object_id, is_active=True).first()
        if template is None:
            raise Http404
        if not self.has_view_permission(request, template):
            return HttpResponseForbidden()
        query = urlencode({'template': template.pk})
        add_url = reverse('admin:api_parishdocument_add')
        return HttpResponseRedirect(f'{add_url}?{query}')

    @admin.display(description='Créer un document')
    def create_document_link(self, obj):
        if not obj.is_active:
            return 'Modèle désactivé'
        url = reverse(
            'admin:api_parishdocumenttemplate_create_document',
            kwargs={'object_id': obj.pk},
        )
        return format_html('<a href="{}">Créer depuis ce modèle</a>', url)
