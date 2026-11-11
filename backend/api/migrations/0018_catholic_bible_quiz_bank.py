from django.db import migrations


QUESTIONS = [
    ('ancien', 'Genèse', 'Quel fils de Jacob fut vendu par ses frères puis devint intendant en Égypte ?', ['Joseph', 'Benjamin', 'Ruben'], 0, 'Joseph fut vendu par ses frères et devint ensuite le principal administrateur du pays d’Égypte (Genèse 37; 41).'),
    ('ancien', 'Exode', 'Quel repas devait rappeler aux Israélites leur départ d’Égypte ?', ['La Pâque', 'La fête des Tentes', 'La fête des Semaines'], 0, 'Le repas de la Pâque commémore la délivrance d’Égypte (Exode 12).'),
    ('ancien', 'Lévitique', 'À quelle tribu appartenait la famille chargée du service sacerdotal d’Israël ?', ['Lévi', 'Juda', 'Benjamin'], 0, 'Aaron et ses descendants, de la tribu de Lévi, furent établis prêtres (Lévitique 8–9).'),
    ('ancien', 'Nombres', 'Quel homme, avec Josué, encouragea Israël à entrer dans le pays promis ?', ['Caleb', 'Koré', 'Balaam'], 0, 'Caleb et Josué firent confiance à Dieu malgré le rapport décourageant des autres explorateurs (Nombres 13–14).'),
    ('ancien', 'Deutéronome', 'Quel grand commandement d’Israël commence par l’appel à écouter ?', ['Aimer Dieu de tout son cœur, de toute son âme et de toute sa force', 'Construire un palais pour chaque tribu', 'Offrir un sacrifice chaque matin'], 0, 'Le Shema demande d’aimer le Seigneur de tout son cœur, de toute son âme et de toute sa force (Deutéronome 6,4-5).'),
    ('ancien', 'Josué', 'Quel fleuve le peuple traversa-t-il pour entrer dans le pays promis ?', ['Le Jourdain', 'Le Nil', 'Le Tigre'], 0, 'Le peuple traversa le Jourdain à pied sec sous la conduite de Josué (Josué 3–4).'),
    ('ancien', 'Juges', 'Quel juge, aidé de trois cents hommes, vainquit les Madianites ?', ['Gédéon', 'Samson', 'Jephté'], 0, 'Gédéon conduisit trois cents hommes contre le camp de Madiane (Juges 7).'),
    ('ancien', 'Ruth', 'Dans quel village Ruth et Naomi arrivèrent-elles à l’époque de la moisson de l’orge ?', ['Bethléem', 'Béthel', 'Silo'], 0, 'Ruth et Naomi arrivèrent à Bethléem au début de la moisson de l’orge (Ruth 1,19-22).'),
    ('ancien', '1 Samuel', 'Quel prophète consacra David comme futur roi alors qu’il était encore jeune ?', ['Samuel', 'Nathan', 'Élie'], 0, 'Samuel oignit David au milieu de ses frères (1 Samuel 16,1-13).'),
    ('ancien', '2 Samuel', 'Quelle ville David établit-il comme capitale de son royaume ?', ['Jérusalem', 'Hébron', 'Samarie'], 0, 'David prit la forteresse de Sion et l’appela Cité de David (2 Samuel 5,6-9).'),
    ('ancien', '1 Rois', 'Quel prophète annonça à Salomon que le royaume serait divisé après son règne ?', ['Ahiyya de Silo', 'Élisée', 'Michée'], 0, 'Le prophète Ahiyya annonça à Jéroboam la division du royaume (1 Rois 11,29-39).'),
    ('ancien', '2 Rois', 'Quel général syrien fut guéri de la lèpre après s’être baigné dans le Jourdain ?', ['Naaman', 'Hazaël', 'Ben-Hadad'], 0, 'Naaman fut guéri après avoir obéi à la parole d’Élisée et s’être plongé sept fois dans le Jourdain (2 Rois 5).'),
    ('ancien', '1 Chroniques', 'Quel roi est au centre des généalogies et des préparatifs du Temple dans ce livre ?', ['David', 'Saül', 'Achab'], 0, 'Les Chroniques retracent la lignée de David et racontent ses préparatifs pour le Temple (1 Chroniques 17; 22).'),
    ('ancien', '2 Chroniques', 'Quel roi inaugura le Temple de Jérusalem par une grande prière ?', ['Salomon', 'Josias', 'Ézéchias'], 0, 'Salomon pria lors de la dédicace du Temple de Jérusalem (2 Chroniques 6–7).'),
    ('ancien', 'Esdras', 'Quel scribe enseigna la Loi au peuple revenu d’exil ?', ['Esdras', 'Néhémie', 'Zorobabel'], 0, 'Esdras, prêtre et scribe, lut et expliqua la Loi au peuple (Esdras 7; Néhémie 8).'),
    ('ancien', 'Néhémie', 'Quel ouvrage les habitants reconstruisirent-ils malgré l’opposition de leurs voisins ?', ['Les murailles de Jérusalem', 'Le palais de Babylone', 'Le port de Jaffa'], 0, 'Néhémie organisa la reconstruction des murailles de Jérusalem (Néhémie 2–6).'),
    ('ancien', 'Tobie', 'Quel ange accompagne Tobie sous l’apparence d’un voyageur ?', ['Raphaël', 'Michel', 'Gabriel'], 0, 'Raphaël accompagne Tobie et révèle ensuite sa mission angélique (Tobie 5; 12).'),
    ('ancien', 'Judith', 'Quel chef ennemi Judith met-elle à mort pour sauver Béthulie ?', ['Holopherne', 'Nabuchodonosor', 'Sennachérib'], 0, 'Judith entre dans le camp ennemi et met fin à la menace d’Holopherne (Judith 12–13).'),
    ('ancien', 'Esther', 'Quel parent Esther appelle-t-elle à rassembler les Juifs pour jeûner avant son audience ?', ['Mardochée', 'Tobie', 'Esdras'], 0, 'Esther demande à Mardochée de réunir les Juifs et de jeûner avant qu’elle se présente au roi (Esther 4,15-17).'),
    ('ancien', '1 Maccabées', 'Quel chef de la famille des Maccabées lança la révolte contre les persécutions séleucides ?', ['Judas Maccabée', 'Simon Pierre', 'Éléazar ben Yair'], 0, 'Judas Maccabée prit la tête de la résistance et contribua à la purification du Temple (1 Maccabées 3–4).'),
    ('ancien', '2 Maccabées', 'Quel exemple de fidélité à la Loi est raconté avec une mère et ses sept fils ?', ['Leur martyre sous la persécution', 'Leur fuite vers l’Égypte', 'La construction de l’arche'], 0, 'Une mère et ses sept fils préfèrent mourir plutôt que d’abandonner la Loi (2 Maccabées 7).'),
    ('ancien', 'Job', 'Que fait Job après avoir appris la perte de ses biens et de ses enfants ?', ['Il bénit le Seigneur malgré son deuil', 'Il devient roi de Jérusalem', 'Il quitte définitivement son pays'], 0, 'Job souffre profondément mais bénit le Seigneur au milieu de l’épreuve (Job 1,20-22).'),
    ('ancien', 'Psaumes', 'Quel psaume commence par l’image du Seigneur comme berger ?', ['Le psaume 23', 'Le psaume 1', 'Le psaume 150'], 0, 'Le psaume 23 exprime la confiance en Dieu sous l’image du berger.'),
    ('ancien', 'Proverbes', 'Quelle attitude est présentée comme le commencement de la sagesse ?', ['La crainte du Seigneur', 'La richesse', 'La renommée'], 0, 'Le livre des Proverbes affirme que la crainte du Seigneur est le commencement de la connaissance (Proverbes 1,7).'),
    ('ancien', 'Qohélet', 'Quel mot revient pour exprimer le caractère fugitif des choses humaines ?', ['Vanité', 'Victoire', 'Exil'], 0, 'Qohélet médite sur la vanité et la fragilité des entreprises humaines (Qohélet 1,2).'),
    ('ancien', 'Cantique des Cantiques', 'Quel thème domine le Cantique des Cantiques ?', ['L’amour célébré dans un poème', 'La sortie d’Égypte', 'La succession des rois'], 0, 'Le Cantique est un poème biblique qui célèbre l’amour et la beauté des bien-aimés.'),
    ('ancien', 'Sagesse', 'Quel roi est associé à la méditation sur la sagesse dans les premiers chapitres du livre ?', ['Salomon', 'David', 'Josias'], 0, 'Le livre met en scène un roi parlant de la sagesse, traditionnellement identifié à Salomon (Sagesse 7–9).'),
    ('ancien', 'Siracide', 'Quel maître est traditionnellement présenté comme l’auteur de ce livre de sagesse ?', ['Jésus, fils de Sirach', 'Isaïe', 'Baruch'], 0, 'Le prologue grec attribue l’enseignement au sage Jésus, fils de Sirach.'),
    ('ancien', 'Isaïe', 'Quel signe le prophète Isaïe annonce-t-il au roi Achaz ?', ['La jeune femme qui enfantera un fils appelé Emmanuel', 'Une tour de feu à Jéricho', 'Le retour d’Élie au Carmel'], 0, 'Isaïe annonce le signe d’Emmanuel dans le contexte de la crise du roi Achaz (Isaïe 7,14).'),
    ('ancien', 'Jérémie', 'Quel objet Jérémie porte-t-il pour annoncer la soumission à Babylone ?', ['Un joug', 'Une couronne d’or', 'Une lampe éteinte'], 0, 'Jérémie porte un joug pour signifier que les nations seront soumises au roi de Babylone (Jérémie 27).'),
    ('ancien', 'Lamentations', 'Quelle ville détruite est pleurée dans les Lamentations ?', ['Jérusalem', 'Ninive', 'Tyr'], 0, 'Les Lamentations expriment le deuil après la chute de Jérusalem.'),
    ('ancien', 'Baruch', 'À quel peuple Baruch lit-il les paroles de confession et de sagesse ?', ['Aux exilés d’Israël à Babylone', 'Aux marins de Ninive', 'Aux habitants de Rome'], 0, 'Baruch s’adresse aux exilés et leur transmet confession, prière et enseignement (Baruch 1–3).'),
    ('ancien', 'Ézéchiel', 'Quel signe d’espérance Ézéchiel voit-il dans la vallée ?', ['Des ossements qui reprennent vie', 'Une mer de feu', 'Une échelle vers Babylone'], 0, 'La vision des ossements desséchés annonce la restauration d’Israël (Ézéchiel 37,1-14).'),
    ('ancien', 'Daniel', 'Quels trois jeunes gens sont jetés dans la fournaise ?', ['Ananias, Azarias et Misaël', 'Pierre, Jacques et Jean', 'Caïn, Abel et Seth'], 0, 'Les trois compagnons de Daniel restent fidèles à Dieu dans la fournaise (Daniel 3).'),
    ('ancien', 'Osée', 'Quel prophète prend son mariage comme signe de la relation entre Dieu et Israël ?', ['Osée', 'Amos', 'Aggée'], 0, 'La vie conjugale d’Osée devient un signe de l’amour fidèle de Dieu envers Israël (Osée 1–3).'),
    ('ancien', 'Joël', 'Quel événement naturel Joël décrit-il comme un appel à la conversion ?', ['Une invasion de sauterelles', 'Un tremblement de terre à Rome', 'Une sécheresse du Nil'], 0, 'Joël décrit une dévastation par les sauterelles et appelle le peuple à revenir au Seigneur (Joël 1–2).'),
    ('ancien', 'Amos', 'Quel métier Amos exerçait-il avant d’être envoyé prophétiser ?', ['Éleveur et cultivateur de sycomores', 'Pêcheur sur le lac', 'Scribe du palais'], 0, 'Amos se présente comme éleveur et cultivateur de sycomores avant sa mission (Amos 7,14-15).'),
    ('ancien', 'Abdias', 'Contre quel peuple le livre d’Abdias prononce-t-il principalement un oracle ?', ['Édom', 'Égypte', 'Moab'], 0, 'L’oracle d’Abdias dénonce l’orgueil et la violence d’Édom contre Juda.'),
    ('ancien', 'Jonas', 'Quelle ville païenne se convertit après la prédication de Jonas ?', ['Ninive', 'Babylone', 'Antioche'], 0, 'Les habitants de Ninive croient en Dieu et se détournent de leur mauvaise conduite (Jonas 3).'),
    ('ancien', 'Michée', 'Dans quelle petite ville Michée annonce-t-il la naissance du chef d’Israël ?', ['Bethléem', 'Sichem', 'Jéricho'], 0, 'Michée annonce qu’un chef pour Israël viendra de Bethléem (Michée 5,1).'),
    ('ancien', 'Nahum', 'Quelle grande ville est annoncée comme devant tomber dans le livre de Nahum ?', ['Ninive', 'Jérusalem', 'Suse'], 0, 'Nahum annonce la chute de Ninive, capitale assyrienne.'),
    ('ancien', 'Habaquq', 'Quelle réponse du prophète exprime la confiance même lorsque les récoltes manquent ?', ['Je me réjouirai dans le Seigneur', 'Je bâtirai une nouvelle tour', 'Je retournerai en Égypte'], 0, 'Habaquq affirme sa joie en Dieu même si les récoltes et les troupeaux viennent à manquer (Habaquq 3,17-19).'),
    ('ancien', 'Sophonie', 'Quel jour de jugement et de salut est au cœur de la prédication de Sophonie ?', ['Le jour du Seigneur', 'Le jour de la traversée du Jourdain', 'Le jour du couronnement de David'], 0, 'Sophonie annonce le jour du Seigneur, qui appelle au jugement et ouvre aussi une espérance de salut.'),
    ('ancien', 'Aggée', 'À quel chantier Aggée exhorte-t-il le peuple revenu d’exil ?', ['La reconstruction du Temple', 'La muraille de Ninive', 'Le palais de Pharaon'], 0, 'Aggée encourage le peuple à reprendre la reconstruction du Temple de Jérusalem (Aggée 1).'),
    ('ancien', 'Zacharie', 'Quel roi est décrit comme venant humblement monté sur un ânon ?', ['Le roi annoncé par Zacharie', 'Le roi de Babylone', 'Le pharaon de l’Exode'], 0, 'Zacharie annonce un roi humble qui vient monté sur un ânon (Zacharie 9,9).'),
    ('ancien', 'Malachie', 'Quel messager Malachie annonce-t-il avant la venue du jour du Seigneur ?', ['Élie', 'Moïse', 'Samuel'], 0, 'Malachie annonce l’envoi du prophète Élie avant le jour du Seigneur (Malachie 3,23-24).'),
    ('nouveau', 'Matthieu', 'Dans quelle ville les mages viennent-ils chercher le roi des Juifs nouveau-né ?', ['Bethléem', 'Nazareth', 'Jéricho'], 0, 'Les mages se rendent à Bethléem après avoir suivi l’étoile (Matthieu 2,1-11).'),
    ('nouveau', 'Marc', 'Quel homme est aidé par Simon de Cyrène pour porter la croix de Jésus ?', ['Jésus', 'Barabbas', 'Pilate'], 0, 'Simon de Cyrène est réquisitionné pour porter la croix de Jésus (Marc 15,21).'),
    ('nouveau', 'Luc', 'Quel ange annonce à Marie qu’elle donnera naissance à Jésus ?', ['Gabriel', 'Raphaël', 'Michel'], 0, 'L’ange Gabriel annonce à Marie la naissance de Jésus (Luc 1,26-38).'),
    ('nouveau', 'Jean', 'Quel disciple reconnaît Jésus ressuscité au bord du lac en disant : « C’est le Seigneur » ?', ['Le disciple que Jésus aimait', 'Thomas', 'Judas Iscariote'], 0, 'Le disciple bien-aimé reconnaît Jésus au bord du lac (Jean 21,7).'),
    ('nouveau', 'Actes des Apôtres', 'Quel couple accueille Paul et travaille avec lui à Corinthe ?', ['Ananie et Saphire', 'Aquilas et Priscille', 'Zacharie et Élisabeth'], 1, 'Aquilas et Priscille accueillent Paul et travaillent avec lui à Corinthe (Actes 18,1-3).'),
    ('nouveau', 'Romains', 'Selon Paul, quel don de Dieu est offert en Jésus Christ ?', ['La vie éternelle', 'Un royaume terrestre immédiat', 'La richesse garantie'], 0, 'Paul affirme que le don gratuit de Dieu est la vie éternelle dans le Christ Jésus (Romains 6,23).'),
    ('nouveau', '1 Corinthiens', 'Quelle vertu Paul place-t-il au-dessus de la foi et de l’espérance ?', ['L’amour', 'La prudence', 'La force'], 0, 'Paul conclut que l’amour est la plus grande de ces trois vertus (1 Corinthiens 13,13).'),
    ('nouveau', '2 Corinthiens', 'Quelle réponse le Seigneur donne-t-il à Paul au sujet de sa faiblesse ?', ['Ma grâce te suffit', 'Tu n’auras plus aucune épreuve', 'Retourne à Jérusalem'], 0, 'Le Seigneur répond à Paul : « Ma grâce te suffit » (2 Corinthiens 12,9).'),
    ('nouveau', 'Galates', 'Quel fruit de l’Esprit Paul cite-t-il en premier ?', ['L’amour', 'La richesse', 'La renommée'], 0, 'Paul commence sa liste des fruits de l’Esprit par l’amour (Galates 5,22).'),
    ('nouveau', 'Éphésiens', 'Quelle image Paul utilise-t-il pour inviter les croyants à tenir ferme ?', ['L’armure de Dieu', 'Une couronne de laurier', 'Une barque de pêche'], 0, 'Paul décrit l’armure de Dieu pour résister au mal (Éphésiens 6,10-17).'),
    ('nouveau', 'Philippiens', 'Dans quelle ville Paul et Silas sont-ils emprisonnés avant qu’un tremblement de terre ouvre les portes ?', ['Philippes', 'Corinthe', 'Éphèse'], 0, 'Paul et Silas sont emprisonnés à Philippes et le geôlier finit par croire (Actes 16,11-34).'),
    ('nouveau', 'Colossiens', 'Qui est présenté comme l’image du Dieu invisible et le premier-né de toute créature ?', ['Le Christ', 'Moïse', 'Jean-Baptiste'], 0, 'L’hymne de Colossiens proclame la primauté du Christ et son rôle dans la création (Colossiens 1,15-20).'),
    ('nouveau', '1 Thessaloniciens', 'Que demande Paul aux croyants de faire sans cesse ?', ['Prier', 'Jeûner toute l’année', 'Voyager à Rome'], 0, 'Paul exhorte à prier sans cesse et à rendre grâce (1 Thessaloniciens 5,16-18).'),
    ('nouveau', '2 Thessaloniciens', 'Quelle règle Paul rappelle-t-il à propos de celui qui refuse de travailler ?', ['Qu’il ne mange pas non plus', 'Qu’il devienne chef de la communauté', 'Qu’il quitte la ville'], 0, 'Paul rappelle que celui qui ne veut pas travailler ne doit pas non plus manger (2 Thessaloniciens 3,10).'),
    ('nouveau', '1 Timothée', 'Quel conseil Paul donne-t-il à Timothée au sujet de son jeune âge ?', ['Que personne ne méprise sa jeunesse; qu’il soit un modèle', 'Qu’il cesse d’enseigner', 'Qu’il quitte Éphèse sans délai'], 0, 'Timothée doit être un modèle par sa parole, sa conduite, l’amour, la foi et la pureté (1 Timothée 4,12).'),
    ('nouveau', '2 Timothée', 'À quoi l’Écriture est-elle utile selon la lettre ?', ['À enseigner et à former à la justice', 'À garantir la richesse', 'À prédire chaque date future'], 0, 'L’Écriture est utile pour enseigner, réfuter, redresser et former à la justice (2 Timothée 3,16).'),
    ('nouveau', 'Tite', 'Sur quelle île Tite est-il chargé d’organiser les communautés ?', ['La Crète', 'Chypre', 'Malte'], 0, 'Paul rappelle avoir laissé Tite en Crète pour organiser les communautés (Tite 1,5).'),
    ('nouveau', 'Philémon', 'Quel esclave devenu chrétien Paul recommande-t-il à Philémon ?', ['Onésime', 'Épaphras', 'Démas'], 0, 'Paul demande à Philémon d’accueillir Onésime comme un frère bien-aimé (Philémon 10-16).'),
    ('nouveau', 'Hébreux', 'Qui est présenté comme grand prêtre selon l’ordre de Melchisédech ?', ['Jésus', 'Aaron', 'Zacharie'], 0, 'La lettre présente Jésus comme grand prêtre selon l’ordre de Melchisédech (Hébreux 5–7).'),
    ('nouveau', 'Jacques', 'Comment Jacques décrit-il la foi qui n’est accompagnée d’aucune œuvre ?', ['Morte', 'Parfaite', 'Inutile seulement pour les riches'], 0, 'Jacques affirme que la foi sans les œuvres est morte (Jacques 2,17).'),
    ('nouveau', '1 Pierre', 'Quelle image Pierre emploie-t-il pour décrire l’ennemi qui rôde ?', ['Un lion rugissant', 'Un serpent de bronze', 'Un aigle blessé'], 0, 'Pierre invite à la vigilance face au diable, comparé à un lion rugissant (1 Pierre 5,8).'),
    ('nouveau', '2 Pierre', 'Quel événement passé Pierre rappelle-t-il comme avertissement contre l’impiété ?', ['Le déluge', 'La chute de Jéricho', 'La destruction de Ninive par Jonas'], 0, 'La lettre rappelle le déluge comme jugement et avertissement (2 Pierre 2,5; 3,5-6).'),
    ('nouveau', '1 Jean', 'Quel signe permet de reconnaître que l’on demeure dans la lumière ?', ['Aimer son frère ou sa sœur', 'Posséder de grandes richesses', 'Ne jamais rencontrer d’épreuve'], 0, 'La lettre enseigne que celui qui aime son frère demeure dans la lumière (1 Jean 2,9-11).'),
    ('nouveau', '2 Jean', 'Quel commandement l’auteur rappelle-t-il à la communauté ?', ['S’aimer les uns les autres', 'Construire un temple à Rome', 'Ne plus accueillir aucun voyageur'], 0, 'La lettre rappelle le commandement de s’aimer les uns les autres (2 Jean 5-6).'),
    ('nouveau', '3 Jean', 'Quel membre de la communauté est loué pour son hospitalité envers les frères ?', ['Gaïus', 'Diotrèphe', 'Démas'], 0, 'L’auteur loue Gaïus pour sa fidélité et son accueil des frères (3 Jean 5-8).'),
    ('nouveau', 'Jude', 'Quel archange est mentionné dans la discussion au sujet du corps de Moïse ?', ['Michel', 'Gabriel', 'Raphaël'], 0, 'La lettre de Jude mentionne l’archange Michel dans cette discussion (Jude 9).'),
    ('nouveau', 'Apocalypse', 'Combien de communautés d’Asie reçoivent les messages au début du livre ?', ['Sept', 'Douze', 'Quarante'], 0, 'L’Apocalypse adresse des messages à sept Églises d’Asie (Apocalypse 1–3).'),
]


def seed_catholic_canon_questions(apps, schema_editor):
    Question = apps.get_model('api', 'QuizQuestion')
    Question.objects.bulk_create([
        Question(
            testament=testament,
            category=book,
            prompt=prompt,
            options=options,
            correct_option=correct_option,
            explanation=explanation,
            is_active=True,
        )
        for testament, book, prompt, options, correct_option, explanation in QUESTIONS
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_quiz_games'),
    ]

    operations = [
        migrations.RunPython(seed_catholic_canon_questions, migrations.RunPython.noop),
    ]
