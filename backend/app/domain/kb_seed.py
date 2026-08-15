"""Seed knowledge base — French and Arabic.

Templates are what an agent actually sends, so they are written as a bank would
write them: acknowledge, state what happens next, give a deadline. No promises
the system cannot keep, and no apology that admits liability.

Two obligations from the circulaire shape every template here:

*   **Article 7** requires the bank to inform customers of the handling delays
    *and of how to reach the banking mediator*. So the mediation route is named
    in the acknowledgement rather than buried on a website.
*   **Article 8** caps the reply at fifteen working days from the acknowledgement.
    Templates quote {{sla_days}} — the internal target for that category — and
    never a figure above the legal ceiling.
"""

from typing import Any

from app.domain.taxonomy import Category

GREETING_FR = "Bonjour {{claimant_name}},\n\n"
GREETING_AR = "السلام عليكم {{claimant_name}}،\n\n"

#: Article 7. Identical on every reply, because the obligation is not optional.
MEDIATION_FR = (
    "\n\nSi la reponse apportee ne vous satisfait pas, vous pouvez saisir le "
    "mediateur bancaire, conformement a la reglementation en vigueur."
)
MEDIATION_AR = (
    "\n\nإذا لم يقنعكم الرد، يمكنكم اللجوء إلى الوسيط البنكي طبقا للتراتيب "
    "الجاري بها العمل."
)

CLOSING_FR = (
    MEDIATION_FR + "\n\nNous restons a votre disposition.\n"
    "Service Reclamations — {{department}}"
)
CLOSING_AR = MEDIATION_AR + "\n\nنبقى على ذمتكم.\nمصلحة الشكاوى — {{department}}"


def _ack(body: str) -> str:
    """Standard acknowledgement (Article 8: reference, date, then the delay)."""
    return (
        GREETING_FR
        + "Votre reclamation {{ref}} concernant {{category}} a bien ete "
        "enregistree le {{created_at}}.\n\n" + body + "\n\n"
        "Notre equipe {{department}} traite votre demande dans un delai de "
        "{{sla_days}} jours ouvrables." + CLOSING_FR
    )


def _ack_ar(body: str) -> str:
    return (
        GREETING_AR
        + "تم تسجيل شكواكم {{ref}} بتاريخ {{created_at}}.\n\n" + body + "\n\n"
        "تتولى مصلحة {{department}} معالجة طلبكم في أجل {{sla_days}} أيام عمل."
        + CLOSING_AR
    )


KB_SEED: list[dict[str, Any]] = [
    # -------------------------------------------------------- CARTE_BANCAIRE
    {
        "title": "Carte avalee ou bloquee — procedure",
        "category": Category.CARTE_BANCAIRE,
        "language": "fr",
        "tags": ["carte", "avalee", "bloquee", "opposition", "distributeur"],
        "content": (
            "Carte avalee : le distributeur la conserve 24 a 48 heures avant "
            "destruction. Identifier l'agence detentrice, verifier l'identite du "
            "porteur, puis restituer ou commander un renouvellement. "
            "Carte bloquee : identifier le motif (code errone trois fois, "
            "suspicion de fraude, impaye) avant toute action."
        ),
        "template": _ack(
            "Nous verifions aupres de l'agence detentrice du distributeur "
            "concerne. Si votre carte a ete conservee, elle vous sera restituee "
            "apres verification de votre identite ; a defaut, une carte de "
            "remplacement sera commandee sans frais."
        ),
    },
    {
        "title": "البطاقة المحتجزة أو المعطلة",
        "category": Category.CARTE_BANCAIRE,
        "language": "ar",
        "tags": ["بطاقة", "الموزع", "تعطيل", "اعتراض"],
        "content": "إجراءات استرجاع البطاقة المحتجزة لدى الموزع الآلي أو رفع التعطيل.",
        "template": _ack_ar(
            "نقوم بالتثبت لدى الوكالة المعنية بالموزع الآلي. في صورة حجز البطاقة، "
            "يتم إرجاعها إليكم بعد التثبت من هويتكم، وإلا يتم إصدار بطاقة بديلة "
            "دون مصاريف."
        ),
    },
    # --------------------------------------------------------------- DAB_GAB
    {
        "title": "Retrait debite sans delivrance de billets",
        "category": Category.DAB_GAB,
        "language": "fr",
        "tags": ["distributeur", "retrait", "billets", "compensation"],
        "content": (
            "Rapprocher le journal electronique du distributeur avec le "
            "mouvement du compte : si les billets n'ont pas ete delivres, "
            "l'ecart apparait a l'arrete de caisse. Pour un distributeur d'une "
            "autre banque, la regularisation passe par la compensation "
            "interbancaire — annoncer le delai reel plutot qu'une date."
        ),
        "template": _ack(
            "Nous rapprochons le journal du distributeur concerne avec les "
            "mouvements de votre compte. Si l'operation n'a pas ete honoree, le "
            "montant vous sera recredite avec la date de valeur d'origine."
        ),
    },
    {
        "title": "خصم دون تسليم الأوراق النقدية",
        "category": Category.DAB_GAB,
        "language": "ar",
        "tags": ["الموزع", "سحب", "خصم", "إرجاع"],
        "content": "مقارنة سجل الموزع الآلي بحركة الحساب وإرجاع المبلغ عند ثبوت عدم التسليم.",
        "template": _ack_ar(
            "نقوم بمقارنة سجل الموزع الآلي بحركات حسابكم. في صورة عدم تنفيذ "
            "العملية، يتم إرجاع المبلغ إلى حسابكم بتاريخ القيمة الأصلي."
        ),
    },
    # ------------------------------------------------ PAIEMENT_TPE_ECOMMERCE
    {
        "title": "Double debit ou paiement refuse",
        "category": Category.PAIEMENT_TPE_ECOMMERCE,
        "language": "fr",
        "tags": ["tpe", "double debit", "3d secure", "commercant"],
        "content": (
            "Double debit : demander le ticket du commercant, distinguer une "
            "pre-autorisation non levee (elle tombe seule sous sept jours) "
            "d'une double capture (a annuler). Paiement refuse : verifier le "
            "plafond, l'activation e-commerce et le numero enregistre pour le "
            "code 3D Secure."
        ),
        "template": _ack(
            "Nous verifions aupres du commercant et de notre centre monetique "
            "s'il s'agit d'une double capture ou d'une pre-autorisation non "
            "levee. Tout montant preleve a tort vous sera restitue."
        ),
    },
    # -------------------------------------------------- VIREMENT_PRELEVEMENT
    {
        "title": "Virement non recu — tracage",
        "category": Category.VIREMENT_PRELEVEMENT,
        "language": "fr",
        "tags": ["virement", "rib", "salaire", "tracage"],
        "content": (
            "Verifier d'abord le RIB saisi et la date d'execution : un virement "
            "vers une autre banque passe par la compensation, soit un jour "
            "ouvre. Au-dela, ouvrir une demande de tracage. Si le RIB etait "
            "errone, seule une demande de restitution aupres de la banque "
            "beneficiaire est possible — le dire d'emblee."
        ),
        "template": _ack(
            "Nous tracons l'operation aupres de la banque beneficiaire et vous "
            "communiquerons la date effective de credit ainsi que la reference "
            "interbancaire."
        ),
    },
    {
        "title": "التحويل غير الواصل",
        "category": Category.VIREMENT_PRELEVEMENT,
        "language": "ar",
        "tags": ["تحويل", "أجرة", "تتبع"],
        "content": "التثبت من المعرف البنكي وتاريخ التنفيذ ثم تتبع العملية لدى البنك المستفيد.",
        "template": _ack_ar(
            "نقوم بتتبع العملية لدى البنك المستفيد وسنوافيكم بتاريخ الإيداع "
            "الفعلي وبمرجع العملية."
        ),
    },
    # ---------------------------------------------------------- CHEQUE_EFFET
    {
        "title": "Chequier non delivre ou cheque rejete",
        "category": Category.CHEQUE_EFFET,
        "language": "fr",
        "tags": ["cheque", "chequier", "provision", "rejet"],
        "content": (
            "Rejet pour defaut de provision : verifier le solde a la date de "
            "presentation, non a la date de reclamation, ainsi que l'ordre "
            "d'imputation des operations du jour. Un rejet errone se regularise "
            "sans delai — ses consequences pour le client depassent le montant."
        ),
        "template": _ack(
            "Nous verifions le solde de votre compte a la date exacte de "
            "presentation du cheque ainsi que l'ordre d'imputation des "
            "operations. Si le rejet s'avere injustifie, nous procederons a la "
            "regularisation et vous remettrons une attestation."
        ),
    },
    # -------------------------------------------------------- COMPTE_GESTION
    {
        "title": "Cloture de compte et releves",
        "category": Category.COMPTE_GESTION,
        "language": "fr",
        "tags": ["cloture", "releve", "compte", "procuration"],
        "content": (
            "Cloture : verifier l'absence d'operations en cours, de cheques non "
            "presentes et d'engagements rattaches, recuperer les moyens de "
            "paiement, puis solder. Les frais cessent a la date de cloture "
            "effective, pas a celle de la demande — tout prelevement posterieur "
            "est a rembourser."
        ),
        "template": _ack(
            "Nous verifions l'etat de votre compte, les operations en cours et "
            "les moyens de paiement a restituer. Tout frais preleve apres la "
            "date de cloture effective vous sera rembourse."
        ),
    },
    {
        "title": "غلق الحساب وكشوفات الحساب",
        "category": Category.COMPTE_GESTION,
        "language": "ar",
        "tags": ["حساب", "غلق", "كشف"],
        "content": "إجراءات غلق الحساب وإرجاع المصاريف المقتطعة بعد تاريخ الغلق الفعلي.",
        "template": _ack_ar(
            "نتثبت من وضعية حسابكم ومن العمليات الجارية ووسائل الدفع الواجب "
            "إرجاعها. كل مصاريف مقتطعة بعد تاريخ الغلق الفعلي سيتم إرجاعها."
        ),
    },
    # ---------------------------------------------------- CREDIT_FINANCEMENT
    {
        "title": "Echeance, mainlevee et dossier de credit",
        "category": Category.CREDIT_FINANCEMENT,
        "language": "fr",
        "tags": ["credit", "echeance", "mainlevee", "amortissement"],
        "content": (
            "Double prelevement d'echeance : rembourser puis corriger le "
            "tableau d'amortissement, faute de quoi l'ecart se propage sur "
            "toute la duree. Mainlevee : delivrable seulement apres solde total, "
            "et elle debloque souvent une vente — la traiter comme urgente."
        ),
        "template": _ack(
            "Nous verifions les echeances prelevees et, le cas echeant, "
            "corrigeons le tableau d'amortissement avant de vous le communiquer "
            "a jour."
        ),
    },
    # ----------------------------------------------------- FRAIS_COMMISSIONS
    {
        "title": "Contestation de frais et agios",
        "category": Category.FRAIS_COMMISSIONS,
        "language": "fr",
        "tags": ["frais", "agios", "commission", "tarification"],
        "content": (
            "Reconstituer le calcul jour par jour a partir des soldes en date "
            "de valeur et le communiquer : un client qui voit le detail conteste "
            "rarement deux fois. Verifier que la ligne figure dans la convention "
            "signee ; a defaut, elle est a rembourser."
        ),
        "template": _ack(
            "Nous reconstituons le detail du calcul a partir des soldes en date "
            "de valeur et verifions sa conformite a la convention que vous avez "
            "signee. Le decompte detaille vous sera communique."
        ),
    },
    {
        "title": "الاعتراض على المصاريف والفوائد",
        "category": Category.FRAIS_COMMISSIONS,
        "language": "ar",
        "tags": ["مصاريف", "عمولة", "فوائد"],
        "content": (
            "إعادة احتساب المصاريف انطلاقا من الأرصدة بتاريخ القيمة وموافاة "
            "الحريف بالتفصيل."
        ),
        "template": _ack_ar(
            "نقوم بإعادة احتساب المصاريف انطلاقا من الأرصدة بتاريخ القيمة "
            "والتثبت من مطابقتها للاتفاقية الممضاة، وسنوافيكم بالتفصيل."
        ),
    },
    # ------------------------------------------------------- BANQUE_DIGITALE
    {
        "title": "Acces a la banque en ligne",
        "category": Category.BANQUE_DIGITALE,
        "language": "fr",
        "tags": ["application", "connexion", "otp", "code"],
        "content": (
            "Code bloque apres trois tentatives : deblocage en agence apres "
            "verification d'identite. Code de validation non recu : verifier le "
            "numero de telephone enregistre au dossier — c'est la cause dans la "
            "grande majorite des cas, et le client l'ignore."
        ),
        "template": _ack(
            "Nous verifions l'etat de votre acces ainsi que le numero de "
            "telephone enregistre a votre dossier, qui conditionne la reception "
            "des codes de validation."
        ),
    },
    # -------------------------------------------- OPERATIONS_INTERNATIONALES
    {
        "title": "Allocation touristique et transferts",
        "category": Category.OPERATIONS_INTERNATIONALES,
        "language": "fr",
        "tags": ["allocation", "devise", "transfert", "change"],
        "content": (
            "Allocation touristique : verifier le solde annuel disponible et les "
            "justificatifs de voyage. Tout refus doit etre motive par ecrit — "
            "c'est une exigence de l'article 8, pas une courtoisie. Transfert "
            "recu : verifier le SWIFT et la domiciliation avant de conclure a un "
            "non-recu."
        ),
        "template": _ack(
            "Nous verifions votre solde d'allocation disponible ainsi que les "
            "pieces fournies. Toute decision de refus vous sera communiquee par "
            "ecrit et motivee."
        ),
    },
    # ----------------------------------- FRAUDE_OPERATION_NON_AUTORISEE
    {
        "title": "Operation non autorisee — reflexe immediat",
        "category": Category.FRAUDE_OPERATION_NON_AUTORISEE,
        "language": "fr",
        "tags": ["fraude", "opposition", "non autorisee", "urgence"],
        "content": (
            "Mettre la carte en opposition avant toute analyse : la perte "
            "continue tant que l'instrument reste actif. Recueillir la liste "
            "exacte des operations contestees, la date de derniere utilisation "
            "legitime et la position du porteur. Orienter vers un depot de "
            "plainte. Ne jamais facturer les frais d'opposition a une victime."
        ),
        "template": _ack(
            "Votre carte a ete mise en opposition immediatement. Nous analysons "
            "les operations que vous contestez et les circonstances de leur "
            "realisation. Nous vous invitons a deposer plainte et a nous "
            "transmettre le recepisse, qui appuiera votre dossier."
        ),
    },
    {
        "title": "عملية غير مصرح بها",
        "category": Category.FRAUDE_OPERATION_NON_AUTORISEE,
        "language": "ar",
        "tags": ["احتيال", "اعتراض", "بطاقة"],
        "content": (
            "الاعتراض الفوري على البطاقة ثم تحليل العمليات المتنازع فيها وتوجيه "
            "الحريف لتقديم شكاية."
        ),
        "template": _ack_ar(
            "تم الاعتراض على بطاقتكم فورا. نقوم بتحليل العمليات موضوع النزاع "
            "وظروف إنجازها. ندعوكم إلى تقديم شكاية وموافاتنا بالوصل لدعم ملفكم."
        ),
    },
    # ------------------------------------------------ AGENCE_QUALITE_SERVICE
    {
        "title": "Qualite de l'accueil en agence",
        "category": Category.AGENCE_QUALITE_SERVICE,
        "language": "fr",
        "tags": ["agence", "attente", "accueil", "conseiller"],
        "content": (
            "Recueillir la date, l'heure et l'agence concernee avant toute "
            "reponse : sans cela le retour au directeur d'agence n'a aucune "
            "portee. Repondre au client meme lorsque la suite donnee est "
            "interne — c'est l'absence de reponse qui transforme une remarque en "
            "saisine du mediateur."
        ),
        "template": _ack(
            "Votre remarque a ete transmise au directeur de l'agence concernee. "
            "Nous revenons vers vous sur les mesures prises."
        ),
    },
]
