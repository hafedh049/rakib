"""Seed knowledge base — French and Arabic, one pair per category.

Templates are what an agent actually sends, so they are written as an operator
would write them: acknowledge, state what happens next, give a deadline. No
promises the system cannot keep, and no apology that admits liability.
"""

from typing import Any

from app.domain.taxonomy import Category

GREETING_FR = "Bonjour {{claimant_name}},\n\n"
GREETING_AR = "السلام عليكم {{claimant_name}}،\n\n"
CLOSING_FR = (
    "\n\nNous restons a votre disposition.\nService Reclamations — {{department}}"
)
CLOSING_AR = "\n\nنبقى على ذمتكم.\nمصلحة الشكاوى — {{department}}"

KB_SEED: list[dict[str, Any]] = [
    # ------------------------------------------------------------ FACTURATION
    {
        "title": "Contestation de facture — accuse et delai",
        "category": Category.FACTURATION,
        "language": "fr",
        "tags": ["facture", "montant", "contestation", "prelevement"],
        "content": (
            "Procedure de contestation de facture : verifier le detail de "
            "consommation, comparer avec l'offre souscrite, identifier les "
            "depassements hors forfait, puis emettre un avoir si l'ecart est "
            "confirme. Delai de traitement standard : 72 heures."
        ),
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} concernant {{category}} a bien ete "
            "enregistree le {{created_at}}.\n\n"
            "Nous procedons a la verification detaillee de votre facture. "
            "Si un ecart est confirme, un avoir sera emis sur votre prochaine "
            "echeance.\n\n"
            "Notre equipe {{department}} traite votre demande, delai maximum "
            "{{sla_hours}} heures." + CLOSING_FR
        ),
    },
    {
        "title": "الاعتراض على الفاتورة — إعلام بالاستلام",
        "category": Category.FACTURATION,
        "language": "ar",
        "tags": ["فاتورة", "مبلغ", "اعتراض"],
        "content": (
            "إجراءات الاعتراض على الفاتورة: مراجعة تفاصيل الاستهلاك، مقارنتها "
            "بالعرض المشترك فيه، تحديد التجاوزات، ثم إصدار إشعار بالخصم عند "
            "تأكد الفارق."
        ),
        "template": (
            GREETING_AR
            + "تم تسجيل شكواكم {{ref}} بخصوص {{category}} بتاريخ {{created_at}}.\n\n"
            "نقوم حاليا بمراجعة تفاصيل فاتورتكم، وفي صورة تأكد وجود خطأ سيتم "
            "تعديل المبلغ في الفاتورة القادمة.\n\n"
            "أجل المعالجة الأقصى {{sla_hours}} ساعة." + CLOSING_AR
        ),
    },
    # ------------------------------------------------------ PAIEMENT_RECHARGE
    {
        "title": "Recharge ou paiement non credite",
        "category": Category.PAIEMENT_RECHARGE,
        "language": "fr",
        "tags": ["recharge", "paiement", "solde", "transaction"],
        "content": (
            "Rapprochement bancaire : recuperer la reference de transaction, "
            "verifier aupres du prestataire de paiement, crediter manuellement "
            "si le debit est confirme et non impute. Delai bancaire habituel : "
            "48 a 72 heures."
        ),
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} relative a un paiement non credite est "
            "enregistree depuis le {{created_at}}.\n\n"
            "Nous effectuons le rapprochement avec notre prestataire de "
            "paiement. Si le debit est confirme sans imputation, votre compte "
            "sera credite du montant de {{amount}}.\n\n"
            "Delai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    {
        "title": "تعبئة أو خلاص لم يتم احتسابه",
        "category": Category.PAIEMENT_RECHARGE,
        "language": "ar",
        "tags": ["تعبئة", "خلاص", "رصيد"],
        "content": "مقارنة العملية مع مزود الخلاص وإضافة المبلغ يدويا عند تأكد الخصم.",
        "template": (
            GREETING_AR
            + "تم تسجيل شكواكم {{ref}} حول عملية خلاص لم تُحتسب بتاريخ "
            "{{created_at}}.\n\nنقوم بالتثبت مع مزود الخدمة، وسيتم تعديل رصيدكم "
            "عند تأكد العملية.\n\nأجل المعالجة {{sla_hours}} ساعة." + CLOSING_AR
        ),
    },
    # ---------------------------------------------------------- RESEAU_MOBILE
    {
        "title": "Incident de couverture mobile",
        "category": Category.RESEAU_MOBILE,
        "language": "fr",
        "tags": ["reseau", "couverture", "signal", "panne"],
        "content": (
            "Verifier les incidents en cours sur la zone, relever la delegation "
            "et le gouvernorat, ouvrir un ticket radio si plusieurs signalements "
            "concordent. Une panne collective est traitee en priorite."
        ),
        "template": (
            GREETING_FR
            + "Votre signalement {{ref}} concernant la couverture reseau a ete "
            "transmis a notre equipe technique le {{created_at}}.\n\n"
            "Un diagnostic est en cours sur votre zone. Vous serez informe des "
            "que le service sera retabli.\n\n"
            "Delai d'intervention estime : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    {
        "title": "انقطاع التغطية الجوالة",
        "category": Category.RESEAU_MOBILE,
        "language": "ar",
        "tags": ["شبكة", "تغطية", "انقطاع"],
        "content": "التثبت من الأعطاب الجارية بالمنطقة وفتح تذكرة فنية عند تعدد الإعلامات.",
        "template": (
            GREETING_AR
            + "تم تحويل إعلامكم {{ref}} حول تغطية الشبكة إلى المصلحة الفنية "
            "بتاريخ {{created_at}}.\n\nيجري حاليا تشخيص الوضعية بمنطقتكم وسيتم "
            "إعلامكم فور إصلاح العطب.\n\nالأجل التقديري {{sla_hours}} ساعة."
            + CLOSING_AR
        ),
    },
    # ---------------------------------------------------------- INTERNET_FIXE
    {
        "title": "Panne ADSL ou fibre",
        "category": Category.INTERNET_FIXE,
        "language": "fr",
        "tags": ["adsl", "fibre", "box", "debit", "panne"],
        "content": (
            "Test de ligne a distance, verification de la synchronisation du "
            "modem, planification d'une intervention si le defaut est confirme "
            "sur la boucle locale."
        ),
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} relative a votre connexion fixe est "
            "enregistree depuis le {{created_at}}.\n\n"
            "Un test de ligne a distance est en cours. Si le defaut est confirme "
            "sur la boucle locale, une intervention technique sera planifiee et "
            "vous serez contacte pour convenir d'un creneau.\n\n"
            "Delai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    {
        "title": "عطب الأنترنت القار",
        "category": Category.INTERNET_FIXE,
        "language": "ar",
        "tags": ["أنترنت", "عطب", "صبيب"],
        "content": "اختبار الخط عن بعد وبرمجة تدخل ميداني عند تأكد العطب.",
        "template": (
            GREETING_AR
            + "تم تسجيل شكواكم {{ref}} حول الأنترنت القار بتاريخ {{created_at}}.\n\n"
            "يجري اختبار الخط عن بعد، وفي صورة تأكد العطب ستتم برمجة تدخل فني.\n\n"
            "الأجل الأقصى {{sla_hours}} ساعة." + CLOSING_AR
        ),
    },
    # -------------------------------------------------- INTERVENTION_TECHNIQUE
    {
        "title": "Rendez-vous technique manque ou retarde",
        "category": Category.INTERVENTION_TECHNIQUE,
        "language": "fr",
        "tags": ["technicien", "rendez-vous", "intervention", "delai"],
        "content": (
            "Reprogrammer sous 48 heures, prevenir le client par appel, "
            "escalader au responsable technique si le dossier depasse le delai "
            "annonce."
        ),
        "template": (
            GREETING_FR
            + "Nous avons bien note votre reclamation {{ref}} du {{created_at}} "
            "concernant une intervention technique.\n\n"
            "Nous reprogrammons votre rendez-vous en priorite et un conseiller "
            "vous appellera pour convenir d'un creneau qui vous convient.\n\n"
            "Delai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    # ------------------------------------------------------ OFFRES_ABONNEMENT
    {
        "title": "Promotion ou changement de forfait non applique",
        "category": Category.OFFRES_ABONNEMENT,
        "language": "fr",
        "tags": ["offre", "promotion", "forfait", "engagement"],
        "content": (
            "Verifier la date de souscription, l'eligibilite a la promotion et "
            "l'etat de la commande. Appliquer retroactivement si l'eligibilite "
            "est confirmee."
        ),
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} concernant votre offre a ete enregistree "
            "le {{created_at}}.\n\n"
            "Nous verifions votre eligibilite et la date effective de "
            "souscription. Si la promotion vous etait bien applicable, elle sera "
            "appliquee retroactivement.\n\n"
            "Delai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    # ------------------------------------------------- RESILIATION_PORTABILITE
    {
        "title": "Resiliation ou portabilite en cours",
        "category": Category.RESILIATION_PORTABILITE,
        "language": "fr",
        "tags": ["resiliation", "portabilite", "engagement", "cloture"],
        "content": (
            "Verifier le depot de la demande, l'etat d'engagement et les "
            "impayes. La facturation doit cesser a la date effective de "
            "resiliation."
        ),
        "template": (
            GREETING_FR
            + "Votre demande {{ref}} du {{created_at}} est prise en charge.\n\n"
            "Nous verifions l'etat de votre dossier de resiliation ainsi que "
            "votre situation contractuelle. Toute facturation posterieure a la "
            "date effective de resiliation vous sera remboursee.\n\n"
            "Delai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    {
        "title": "طلب فسخ أو نقل الرقم",
        "category": Category.RESILIATION_PORTABILITE,
        "language": "ar",
        "tags": ["فسخ", "نقل الرقم"],
        "content": "التثبت من تاريخ إيداع المطلب ووضعية الالتزام التعاقدي.",
        "template": (
            GREETING_AR
            + "تم تسجيل مطلبكم {{ref}} بتاريخ {{created_at}}.\n\n"
            "نقوم بالتثبت من وضعية ملفكم، وكل مبلغ تمت فوترته بعد تاريخ الفسخ "
            "الفعلي سيتم إرجاعه.\n\nالأجل الأقصى {{sla_hours}} ساعة." + CLOSING_AR
        ),
    },
    # ------------------------------------------------- SERVICE_CLIENT_AGENCE
    {
        "title": "Qualite d'accueil en agence ou au centre d'appel",
        "category": Category.SERVICE_CLIENT_AGENCE,
        "language": "fr",
        "tags": ["agence", "accueil", "attente", "conseiller"],
        "content": (
            "Identifier l'agence et le creneau, remonter au responsable de "
            "point de vente, repondre au client sous 72 heures."
        ),
        "template": (
            GREETING_FR
            + "Nous avons bien recu votre reclamation {{ref}} du {{created_at}} "
            "concernant la qualite de notre accueil.\n\n"
            "Votre retour a ete transmis au responsable concerne. Nous prenons "
            "ce type de signalement au serieux et vous informerons des suites "
            "donnees.\n\nDelai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    # -------------------------------------------------------------- EQUIPEMENT
    {
        "title": "Materiel defectueux — echange",
        "category": Category.EQUIPEMENT,
        "language": "fr",
        "tags": ["box", "routeur", "decodeur", "sim", "garantie"],
        "content": (
            "Verifier la date de livraison et la garantie, proposer un echange "
            "en agence ou un envoi, recuperer le materiel defectueux."
        ),
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} du {{created_at}} concernant votre "
            "equipement est enregistree.\n\n"
            "Si le materiel est sous garantie, un echange vous sera propose. "
            "Vous pourrez le retirer en agence ou le recevoir a votre "
            "adresse.\n\nDelai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    # --------------------------------------------------- ROAMING_INTERNATIONAL
    {
        "title": "Contestation de frais de roaming",
        "category": Category.ROAMING_INTERNATIONAL,
        "language": "fr",
        "tags": ["roaming", "itinerance", "international", "pass"],
        "content": (
            "Verifier l'activation du pass, les dates de sejour et les "
            "enregistrements du reseau partenaire. Regulariser si le pass etait "
            "actif pendant la periode contestee."
        ),
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} du {{created_at}} concernant des frais "
            "d'itinerance est en cours d'analyse.\n\n"
            "Nous verifions l'activation de votre pass et les enregistrements "
            "aupres du reseau partenaire. Toute facturation indue vous sera "
            "remboursee.\n\nDelai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    # ---------------------------------------------------- APPLICATION_MOBILE
    {
        "title": "Probleme sur l'application mobile",
        "category": Category.APPLICATION_MOBILE,
        "language": "fr",
        "tags": ["application", "connexion", "bug", "mise a jour"],
        "content": (
            "Faire verifier la version installee, vider le cache, tester la "
            "reinitialisation du mot de passe. Remonter au support applicatif "
            "si le defaut est reproductible."
        ),
        "template": (
            GREETING_FR
            + "Votre signalement {{ref}} du {{created_at}} concernant "
            "l'application a bien ete recu.\n\n"
            "Merci de verifier que vous disposez de la derniere version "
            "installee. Si le probleme persiste, notre equipe technique le "
            "reproduira et vous tiendra informe.\n\n"
            "Delai maximum : {{sla_hours}} heures." + CLOSING_FR
        ),
    },
    {
        "title": "مشكل في التطبيق الجوال",
        "category": Category.APPLICATION_MOBILE,
        "language": "ar",
        "tags": ["تطبيق", "تسجيل الدخول", "تحديث"],
        "content": "التثبت من نسخة التطبيق وإعادة تعيين كلمة السر ثم إحالة المشكل للدعم.",
        "template": (
            GREETING_AR
            + "تم استلام إعلامكم {{ref}} حول التطبيق بتاريخ {{created_at}}.\n\n"
            "يرجى التثبت من تحديث التطبيق لآخر نسخة. في صورة تواصل المشكل ستتولى "
            "المصلحة الفنية معالجته.\n\nالأجل الأقصى {{sla_hours}} ساعة." + CLOSING_AR
        ),
    },
    # ------------------------------------------------------------- generique
    {
        "title": "Accuse de reception generique",
        "category": None,
        "language": "fr",
        "tags": ["accuse", "reception", "generique"],
        "content": "Modele neutre lorsqu'aucune categorie n'est encore confirmee.",
        "template": (
            GREETING_FR
            + "Votre reclamation {{ref}} a bien ete enregistree le "
            "{{created_at}}.\n\n"
            "Elle est en cours d'examen par notre equipe {{department}}. "
            "Nous reviendrons vers vous sous {{sla_hours}} heures."
            + CLOSING_FR
        ),
    },
    {
        "title": "إعلام عام بالاستلام",
        "category": None,
        "language": "ar",
        "tags": ["استلام", "عام"],
        "content": "نموذج محايد عندما لا يكون التصنيف مؤكدا بعد.",
        "template": (
            GREETING_AR
            + "تم تسجيل شكواكم {{ref}} بتاريخ {{created_at}}.\n\n"
            "الملف قيد الدرس من طرف مصلحة {{department}}، وسنعود إليكم في أجل "
            "{{sla_hours}} ساعة." + CLOSING_AR
        ),
    },
]
