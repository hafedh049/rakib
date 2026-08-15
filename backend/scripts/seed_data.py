"""Demo content for the seeder: staff, claimants and complaint bodies.

Split out of scripts/seed.py so the seeding *logic* stays readable next to the
data it inserts. The bodies are written the way Tunisians actually write to
their bank: formal French from business accounts, terse derja from younger
claimants, and Arabic script from older ones.
"""

from app.domain.taxonomy import Category
from app.models.user import Role

#: (email, full name, role, department code, skills)
STAFF = [
    ("admin@rakib.tn", "Sonia Trabelsi", Role.ADMIN, None, []),
    ("superviseur1@rakib.tn", "Mehdi Gharbi", Role.SUPERVISOR, None, []),
    ("superviseur2@rakib.tn", "Ines Bouzid", Role.SUPERVISOR, None, []),
    ("agent.mon1@rakib.tn", "Karim Jelassi", Role.AGENT, "MONETIQUE",
     ["carte", "distributeur"]),
    ("agent.mon2@rakib.tn", "Rania Ayari", Role.AGENT, "MONETIQUE",
     ["tpe", "e-commerce"]),
    ("agent.ope1@rakib.tn", "Yassine Chaouch", Role.AGENT, "OPERATIONS",
     ["virement", "cheque"]),
    ("agent.ope2@rakib.tn", "Nadia Belhaj", Role.AGENT, "OPERATIONS", ["virement"]),
    ("agent.cre1@rakib.tn", "Walid Mansouri", Role.AGENT, "CREDITS",
     ["credit", "mainlevee"]),
    ("agent.rc1@rakib.tn", "Olfa Hamdi", Role.AGENT, "RELATION_CLIENT",
     ["compte", "frais"]),
    ("agent.rc2@rakib.tn", "Bilel Khemiri", Role.AGENT, "RELATION_CLIENT",
     ["agence", "accueil"]),
    ("agent.dig1@rakib.tn", "Amel Zouari", Role.AGENT, "DIGITAL",
     ["application", "web"]),
    ("agent.int1@rakib.tn", "Hamza Ben Romdhane", Role.AGENT, "INTERNATIONAL",
     ["change", "transfert"]),
    ("agent.frd1@rakib.tn", "Sofiene Kacem", Role.AGENT, "CONFORMITE_FRAUDE",
     ["fraude", "opposition"]),
]

#: (full name, email, phone, is_vip)
CLAIMANTS = [
    ("Fatma Ben Ali", "fatma.benali@example.tn", "+21620145879", False),
    ("Societe Medina Import", "contact@medina-import.tn", "+21671845200", True),
    ("Sami Ouertani", "sami.ouertani@example.tn", "+21698774512", False),
    ("Leila Nasri", None, "+21622336698", False),
    ("Anis Dridi", "anis.dridi@example.tn", "+21655412003", False),
    ("Cabinet Ben Youssef", "cabinet@benyoussef.tn", "+21673228400", True),
    ("Emna Sassi", "emna.sassi@example.tn", None, False),
    ("Mohamed Zribi", None, "+21627889044", False),
]

#: (category, subject, body)
COMPLAINTS: list[tuple[str, str, str]] = [
    (Category.DAB_GAB, "Retrait de 300 dinars debite sans billets",
     "J'ai effectue un retrait de 300 dinars au distributeur de l'agence du "
     "centre-ville le 08 a 18h40. Aucun billet n'est sorti mais mon compte a "
     "bien ete debite. Reference OP4471902. Je demande le remboursement."),
    (Category.DAB_GAB, "الموزع خذا الفلوس و ما خرجش",
     "عملت سحب 200 دينار في الموزع متاع المرسى و الفلوس تنقصت من الحساب "
     "اما الاوراق ما خرجتش. من عشرة ايام و ما تحلش المشكل."),
    (Category.DAB_GAB, "Distributeur hors service depuis trois semaines",
     "Le distributeur de Mourouj 5 est hors service depuis trois semaines. "
     "C'est le seul de la zone et tous les clients doivent se deplacer."),
    (Category.CARTE_BANCAIRE, "Carte avalee par le distributeur",
     "Ma carte CIB a ete avalee par le distributeur le 12 du mois. Je me suis "
     "presente le lendemain, on m'a dit d'attendre une semaine. Je n'ai "
     "toujours aucune nouvelle et je suis sans moyen de paiement."),
    (Category.CARTE_BANCAIRE, "Carte bloquee sans aucun motif",
     "Ma carte est bloquee depuis dix jours sans qu'aucun motif ne m'ait ete "
     "communique. Mon compte est approvisionne et je n'ai recu ni SMS ni "
     "courrier m'expliquant ce blocage."),
    (Category.CARTE_BANCAIRE, "Renouvellement de carte jamais recu",
     "J'ai demande le renouvellement de ma carte il y a un mois et regle les "
     "frais correspondants. Elle n'est jamais arrivee a l'agence et personne "
     "n'est en mesure de me dire ou elle se trouve."),
    (Category.PAIEMENT_TPE_ECOMMERCE, "Double debit sur un paiement",
     "Un paiement de 245 dinars chez un commercant de Sousse apparait deux "
     "fois sur mon releve. Le commercant confirme n'avoir encaisse qu'une "
     "seule fois et m'a remis son ticket."),
    (Category.PAIEMENT_TPE_ECOMMERCE, "Code 3D Secure jamais recu",
     "Je ne recois jamais le code de confirmation par SMS lors de mes achats "
     "en ligne, ce qui fait echouer toutes mes transactions depuis deux "
     "semaines. Mon numero est pourtant a jour a l'agence."),
    (Category.VIREMENT_PRELEVEMENT, "Virement de 1500 dinars non recu",
     "J'ai emis un virement de 1500 dinars le 05 vers un compte de la meme "
     "banque. Le beneficiaire ne l'a toujours pas recu apres deux semaines et "
     "mon compte a bien ete debite."),
    (Category.VIREMENT_PRELEVEMENT, "Virement de salaire non credite",
     "Mon virement de salaire n'a pas ete credite ce mois alors que mon "
     "employeur confirme l'avoir emis le 28. Cela fait dix jours et je suis "
     "a decouvert."),
    (Category.VIREMENT_PRELEVEMENT, "التحويل ما وصلش",
     "عملت تحويل 800 دينار من اسبوعين و المستفيد ما وصلوش، و الفلوس تنقصت "
     "من الحساب متاعي. نحب حل بسرعة."),
    (Category.CHEQUE_EFFET, "Cheque rejete a tort",
     "Un de mes cheques d'un montant de 680 dinars a ete rejete pour defaut "
     "de provision alors que mon compte etait crediteur ce jour-la. Ce rejet "
     "me cause un prejudice serieux aupres de mon fournisseur."),
    (Category.CHEQUE_EFFET, "Chequier commande et non delivre",
     "J'ai commande un chequier il y a un mois. Il n'est jamais arrive a "
     "l'agence et les frais ont pourtant ete preleves."),
    (Category.COMPTE_GESTION, "Cloture demandee et jamais effectuee",
     "J'ai demande la cloture de mon compte il y a deux mois en agence, avec "
     "un courrier signe. Le compte est toujours actif et des frais continuent "
     "d'etre preleves."),
    (Category.COMPTE_GESTION, "Releves non recus depuis quatre mois",
     "Je ne recois plus mes releves de compte depuis quatre mois, ni par "
     "courrier ni sur l'espace en ligne. J'en ai besoin pour ma comptabilite."),
    (Category.COMPTE_GESTION, "الحساب مسكر بلا اعلام",
     "سكرو الحساب متاعي بلا ما يعلموني و ما فهمتش علاش. كنت نحب نسحب فلوس "
     "و لقيت الحساب موقوف."),
    (Category.CREDIT_FINANCEMENT, "Echeance prelevee deux fois",
     "L'echeance de mon credit logement a ete prelevee deux fois ce mois, "
     "soit 420 dinars debites en trop. Je demande la restitution immediate."),
    (Category.CREDIT_FINANCEMENT, "Mainlevee non delivree",
     "J'ai solde mon credit par anticipation il y a six semaines. La "
     "mainlevee de l'hypotheque n'a toujours pas ete delivree, ce qui bloque "
     "la vente de mon bien."),
    (Category.CREDIT_FINANCEMENT, "Dossier de credit sans reponse",
     "Mon dossier de credit auto d'un montant de 12000 dinars est sans "
     "reponse depuis deux mois. Aucun interlocuteur ne peut me dire ou il en "
     "est."),
    (Category.FRAIS_COMMISSIONS, "Agios injustifies",
     "Des agios de 187 dinars ont ete preleves sur mon compte alors que je "
     "n'ai jamais ete a decouvert. Je demande le detail du calcul."),
    (Category.FRAIS_COMMISSIONS, "Frais de tenue de compte non annonces",
     "Des frais de tenue de compte de 30 dinars sont preleves chaque "
     "trimestre sans que cela ne figure dans la convention que j'ai signee."),
    (Category.FRAIS_COMMISSIONS, "مصاريف ما فهمتهاش",
     "تنقصت مني 120 دينار مصاريف و انا عمري ما كنت في السالب. نحب التفصيل "
     "متاع الحساب."),
    (Category.BANQUE_DIGITALE, "Application inaccessible",
     "L'application mobile est inaccessible depuis une semaine : elle se "
     "ferme immediatement apres la saisie du code. J'ai desinstalle et "
     "reinstalle sans resultat."),
    (Category.BANQUE_DIGITALE, "Code d'acces bloque",
     "Mon code d'acces a l'espace en ligne est bloque depuis la derniere mise "
     "a jour. La procedure de deblocage envoie un lien qui n'arrive jamais."),
    (Category.BANQUE_DIGITALE, "el application ma tekhdemch",
     "el application ma tekhdemch men jomaa, ki nhot el code tetsakker "
     "wa7edha. nzelt w rje3t nzelt w nafs el mochkel."),
    (Category.OPERATIONS_INTERNATIONALES, "Allocation touristique refusee",
     "Ma demande d'allocation touristique a ete refusee sans motif ecrit "
     "alors que je remplis toutes les conditions et que mon voyage est dans "
     "dix jours."),
    (Category.OPERATIONS_INTERNATIONALES, "Transfert depuis la France non credite",
     "Un transfert de 3000 euros emis depuis la France il y a trois semaines "
     "n'est toujours pas credite sur mon compte. Le donneur d'ordre dispose "
     "de la confirmation SWIFT."),
    (Category.FRAUDE_OPERATION_NON_AUTORISEE, "Operations non autorisees",
     "Je constate sur mon releve plusieurs operations que je n'ai jamais "
     "effectuees, pour un total de 4500 dinars. Ma carte est en ma possession "
     "et je n'ai communique mon code a personne. C'est inacceptable."),
    (Category.FRAUDE_OPERATION_NON_AUTORISEE, "Compte vide apres un SMS frauduleux",
     "J'ai recu un SMS se presentant comme provenant de la banque et "
     "demandant mes identifiants. Depuis, des virements de 6000 dinars ont "
     "quitte mon compte sans mon accord. Mon avocat va porter plainte."),
    (Category.FRAUDE_OPERATION_NON_AUTORISEE, "عمليات ما عملتهاش",
     "في الكشف متاعي فما عمليات ما عملتهاش، المجموع 2400 دينار. البطاقة "
     "عندي و ما عطيت الرمز لحتى واحد. نطلب تدخل عاجل."),
    (Category.AGENCE_QUALITE_SERVICE, "Attente excessive en agence",
     "L'attente a l'agence du centre-ville depasse systematiquement une "
     "heure, avec deux guichets ouverts sur cinq. La situation dure depuis "
     "des mois."),
    (Category.AGENCE_QUALITE_SERVICE, "Chargee de clientele injoignable",
     "Ma chargee de clientele est injoignable depuis trois semaines : ni le "
     "telephone ni les courriels n'aboutissent, et aucun remplacant n'est "
     "designe."),
]
