"""Demo seed: departments, staff, and a month of realistic complaints.

    python -m scripts.seed            # idempotent-ish: skips if complaints exist
    python -m scripts.seed --force    # wipe complaints/users and reseed

The complaint bodies are written the way Tunisians actually write to an
operator: formal French from business accounts, terse derja from mobile users,
arabizi from younger claimants, and Arabic script from older ones.
"""

import argparse
import asyncio
import random
from datetime import UTC, datetime, timedelta

from app import db
from app.config import settings
from app.core.security import hash_password
from app.domain.taxonomy import Category
from app.models.complaint import (
    Channel,
    Claimant,
    Complaint,
    Satisfaction,
    Status,
)
from app.models.counter import Counter, next_complaint_ref
from app.models.department import Department
from app.models.user import Role, User
from app.services.seed_service import seed_departments

SEED = 20260908
DEMO_PASSWORD = "Rakib2026!"

STAFF = [
    ("admin@rakib.tn", "Sonia Trabelsi", Role.ADMIN, None, []),
    ("superviseur1@rakib.tn", "Mehdi Gharbi", Role.SUPERVISOR, None, []),
    ("superviseur2@rakib.tn", "Ines Bouzid", Role.SUPERVISOR, None, []),
    ("agent.fact1@rakib.tn", "Karim Jelassi", Role.AGENT, "FACTURATION",
     ["facturation", "recouvrement"]),
    ("agent.fact2@rakib.tn", "Rania Ayari", Role.AGENT, "FACTURATION",
     ["facturation", "paiement"]),
    ("agent.mob1@rakib.tn", "Yassine Chaouch", Role.AGENT, "RESEAU_MOBILE",
     ["reseau", "roaming"]),
    ("agent.mob2@rakib.tn", "Nadia Belhaj", Role.AGENT, "RESEAU_MOBILE", ["reseau"]),
    ("agent.fixe1@rakib.tn", "Walid Mansouri", Role.AGENT, "FIXE_INTERVENTION",
     ["fibre", "adsl"]),
    ("agent.fixe2@rakib.tn", "Olfa Hamdi", Role.AGENT, "FIXE_INTERVENTION",
     ["intervention"]),
    ("agent.com1@rakib.tn", "Bilel Khemiri", Role.AGENT, "COMMERCIAL",
     ["offres", "retention"]),
    ("agent.rc1@rakib.tn", "Amel Zouari", Role.AGENT, "RELATION_CLIENT",
     ["agence", "equipement"]),
    ("agent.si1@rakib.tn", "Hamza Ben Romdhane", Role.AGENT, "DIGITAL_SI",
     ["application", "web"]),
]

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

# (category, subject, body)
COMPLAINTS: list[tuple[str, str, str]] = [
    (Category.FACTURATION, "Facture de janvier anormalement elevee",
     "Bonjour, ma facture du mois de janvier s'eleve a 187 dinars alors que mon forfait "
     "est a 45 dinars par mois. Je n'ai pas change d'offre et je n'ai pas voyage. "
     "Merci de me fournir le detail des consommations hors forfait."),
    (Category.FACTURATION, "Double prelevement sur mon compte",
     "J'ai ete preleve deux fois pour la meme facture de fevrier, le 03 et le 05. "
     "Ma banque confirme les deux operations. Je demande le remboursement immediat."),
    (Category.FACTURATION, "فاتورة غالية برشة",
     "سلام، الفاتورة متاعي هذا الشهر 210 دينار و انا ما بدلتش في العرض. "
     "نحب نعرف علاش هالمبلغ الكبير و نطلب توضيح."),
    (Category.FACTURATION, "Contestation frais de mise en service",
     "On m'a facture 60 dinars de frais de mise en service alors que le conseiller "
     "en agence m'avait confirme la gratuite dans le cadre de la promotion."),
    (Category.PAIEMENT_RECHARGE, "Recharge de 20 dinars non creditee",
     "J'ai recharge 20 dinars via l'application a 19h32, le montant a ete debite de "
     "ma carte mais mon solde n'a pas bouge. Reference de la transaction : TRX8842190."),
    (Category.PAIEMENT_RECHARGE, "Paiement D17 echoue mais debite",
     "Paiement de ma facture via D17 : l'application affiche 'echec' mais le montant "
     "de 78 dinars a bien ete preleve. Merci de regulariser."),
    (Category.PAIEMENT_RECHARGE, "3andi mochkla fel recharge",
     "3malt recharge 10 dinars w ma wsalnich, 3malt 3 marrat w kol mara ynajem "
     "ynajjem yakhou floussi. barcha semaines w mahalitouch el mochkla."),
    (Category.RESEAU_MOBILE, "Aucun reseau a Ezzahra depuis 4 jours",
     "Depuis samedi il n'y a plus aucun signal dans le quartier Ezzahra Sud. "
     "Impossible de passer un appel. Toute la rue est concernee. C'est inacceptable."),
    (Category.RESEAU_MOBILE, "Debit 4G tres faible en soiree",
     "Le debit 4G tombe a moins de 1 Mbps tous les soirs entre 19h et 23h a Sousse "
     "centre. Impossible de regarder une video. Je paye un forfait illimite."),
    (Category.RESEAU_MOBILE, "ما فماش شبكة",
     "من ثلاثة أيام ما فماش شبكة في الحي، لا مكالمات لا أنترنت. "
     "عملت إعلام في الوكالة و ما تحل شيء. هذا غير مقبول."),
    (Category.RESEAU_MOBILE, "Coupures d'appels repetees",
     "Mes appels se coupent au bout de 30 secondes systematiquement depuis "
     "la mise a jour du reseau dans ma zone. Cela affecte mon activite professionnelle."),
    (Category.INTERNET_FIXE, "Fibre en panne depuis une semaine",
     "Ma connexion fibre est totalement coupee depuis le 12. J'ai appele trois fois "
     "le service technique, on me dit a chaque fois 'sous 48 heures'. "
     "Je travaille a domicile, la situation est intenable."),
    (Category.INTERNET_FIXE, "Debit ADSL tres inferieur a l'abonnement",
     "Je suis abonne a une offre 20 Mbps et je mesure 2,3 Mbps en moyenne. "
     "Test effectue plusieurs fois, en filaire, a differentes heures."),
    (Category.INTERNET_FIXE, "Deconnexions toutes les 10 minutes",
     "La box se deconnecte et se reconnecte en permanence depuis l'orage de mardi. "
     "Les voyants passent au rouge puis reviennent. Merci d'intervenir."),
    (Category.INTERVENTION_TECHNIQUE, "Technicien non venu au rendez-vous",
     "Un rendez-vous d'installation etait fixe jeudi entre 9h et 12h. J'ai pris une "
     "journee de conge, personne n'est venu et personne n'a appele."),
    (Category.INTERVENTION_TECHNIQUE, "Ligne coupee apres des travaux",
     "Suite a des travaux de voirie devant l'immeuble, ma ligne fixe est coupee. "
     "Le cable est visiblement sectionne au niveau du trottoir."),
    (Category.INTERVENTION_TECHNIQUE, "Delai d'intervention depasse",
     "Dossier d'intervention ouvert il y a 15 jours, toujours aucune nouvelle. "
     "Le delai annonce etait de 72 heures. Je demande une escalade du dossier."),
    (Category.OFFRES_ABONNEMENT, "Promotion non appliquee sur ma ligne",
     "J'ai souscrit a l'offre promotionnelle annoncee en agence (2 mois offerts) "
     "mais la remise n'apparait sur aucune de mes deux dernieres factures."),
    (Category.OFFRES_ABONNEMENT, "Changement de forfait non pris en compte",
     "J'ai demande le passage a l'offre superieure le 2 du mois. Un mois plus tard "
     "je suis toujours sur l'ancien forfait et facture sur l'ancien tarif."),
    (Category.RESILIATION_PORTABILITE, "Demande de resiliation sans suite",
     "J'ai depose une demande de resiliation en agence il y a trois semaines avec "
     "accuse de reception. Je continue a etre facture. Je saisirai l'INC si necessaire."),
    (Category.RESILIATION_PORTABILITE, "Portabilite bloquee depuis 10 jours",
     "Ma demande de portabilite vers votre reseau est bloquee depuis 10 jours. "
     "Si ce n'est pas regle cette semaine je reste chez mon operateur actuel."),
    (Category.SERVICE_CLIENT_AGENCE, "Attente de deux heures en agence",
     "Deux heures d'attente a l'agence du centre-ville pour une simple remise de SIM, "
     "avec seulement deux guichets ouverts sur six. L'organisation est a revoir."),
    (Category.SERVICE_CLIENT_AGENCE, "Service client injoignable",
     "J'appelle le service client depuis trois jours, la ligne raccroche "
     "automatiquement apres le message d'accueil. Aucun moyen de joindre un conseiller."),
    (Category.SERVICE_CLIENT_AGENCE, "Comportement d'un agent en agence",
     "L'agent qui m'a recu a ete desagreable et a refuse de me donner son nom "
     "lorsque j'ai demande a faire une reclamation. Je souhaite un retour sur ce point."),
    (Category.EQUIPEMENT, "Routeur defectueux recu neuf",
     "Le routeur livre lundi ne s'allume pas du tout. Aucun voyant, testee sur trois "
     "prises differentes. Je demande un echange."),
    (Category.EQUIPEMENT, "Decodeur TV redemarre en boucle",
     "Le decodeur redemarre toutes les cinq minutes depuis la derniere mise a jour. "
     "J'ai deja fait une reinitialisation complete sans resultat."),
    (Category.EQUIPEMENT, "SIM defectueuse",
     "La puce recue en agence n'est pas reconnue par mon telephone ni par un autre "
     "appareil. Le numero est pourtant bien active selon l'agent."),
    (Category.ROAMING_INTERNATIONAL, "Frais de roaming exorbitants",
     "Retour d'un sejour de 5 jours en Italie : 340 dinars de frais de roaming alors "
     "que j'avais souscrit au pass international. Merci de verifier."),
    (Category.ROAMING_INTERNATIONAL, "Appels internationaux surtaxes",
     "Mes appels vers la France sont factures 1,2 dinar la minute au lieu des "
     "0,3 dinar annonces dans l'offre a laquelle j'ai souscrit."),
    (Category.APPLICATION_MOBILE, "Impossible de se connecter a l'application",
     "Depuis la mise a jour de l'application je ne peux plus me connecter. "
     "Le message 'identifiants invalides' s'affiche alors que le mot de passe est bon."),
    (Category.APPLICATION_MOBILE, "Solde affiche incorrect dans l'appli",
     "L'application affiche un solde de 0 dinar alors que j'ai recharge hier. "
     "Le solde est correct quand je compose le code USSD."),
    (Category.APPLICATION_MOBILE, "L'app plante au demarrage",
     "l application tetsakker wa9t nheb nafta7ha, 3malt desinstall w install "
     "w nafs el mochkel. telephone Android jdid."),
]

STATUS_MIX = (
    [Status.NEW] * 8
    + [Status.TRIAGED] * 4
    + [Status.ASSIGNED] * 10
    + [Status.IN_PROGRESS] * 12
    + [Status.PENDING_CLAIMANT] * 4
    + [Status.RESOLVED] * 16
    + [Status.CLOSED] * 5
    + [Status.REJECTED] * 1
)

CHANNEL_MIX = [Channel.WEB] * 7 + [Channel.PHONE] * 2 + [Channel.AGENCE] * 2 + [Channel.EMAIL]


async def main(force: bool = False, count: int = 60, triage: bool = True) -> None:
    random.seed(SEED)
    await db.init_db()

    if force:
        await Complaint.find_all().delete()
        await User.find_all().delete()
        await Counter.find_all().delete()
        print("wiped complaints, users, counters")

    created_departments = await seed_departments()
    departments = {d.code: d for d in await Department.find_all().to_list()}
    print(f"departments: {len(departments)} ({created_departments} created)")

    if await User.find_one(User.email == STAFF[0][0]) is None:
        for email, name, role, dept_code, skills in STAFF:
            await User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=name,
                role=role,
                department_id=departments[dept_code].id if dept_code else None,
                skills=skills,
                max_concurrent=15,
                last_active_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 40)),
            ).insert()
        print(f"staff: {len(STAFF)} created (password: {DEMO_PASSWORD})")

    existing = await Complaint.find_all().count()
    if existing and not force:
        print(f"complaints: {existing} already present — skipping (use --force)")
        await db.close_db()
        return

    agents = await User.find(User.role == Role.AGENT).to_list()
    agents_by_department: dict[str, list[User]] = {}
    for agent in agents:
        for code, department in departments.items():
            if agent.department_id == department.id:
                agents_by_department.setdefault(code, []).append(agent)

    now = datetime.now(UTC)
    for index in range(count):
        category, subject, body = COMPLAINTS[index % len(COMPLAINTS)]
        name, email, phone, is_vip = CLAIMANTS[index % len(CLAIMANTS)]
        status = STATUS_MIX[index % len(STATUS_MIX)]

        # Age follows the status. Spreading every complaint evenly over 30 days
        # left the whole board breached and red, which demonstrates nothing:
        # open work is recent, closed work is older.
        if status in (Status.RESOLVED, Status.CLOSED, Status.REJECTED):
            age_hours = random.randint(48, 30 * 24)
        elif status in (Status.NEW, Status.TRIAGED):
            age_hours = random.randint(0, 6)
        else:
            age_hours = random.randint(2, 60)
        created_at = now - timedelta(hours=age_hours)

        complaint = Complaint(
            ref=await next_complaint_ref(created_at),
            channel=random.choice(CHANNEL_MIX),
            claimant=Claimant(
                full_name=name, email=email, phone=phone, is_vip=is_vip
            ),
            subject=subject,
            body=body,
            status=status,
            created_at=created_at,
            updated_at=created_at,
        )
        complaint.sla.hours = settings.sla_hours_p3
        complaint.sla.due_at = created_at + timedelta(hours=settings.sla_hours_p3)
        if status in (Status.RESOLVED, Status.CLOSED):
            # Closed within its window, so resolution-time analytics are real.
            complaint.sla.resolved_at = created_at + timedelta(
                hours=random.randint(2, 40)
            )
            complaint.satisfaction = (
                Satisfaction(score=random.choice([3, 4, 4, 5, 5, 2]))
                if random.random() < 0.6
                else None
            )
        complaint.log("complaint.created", channel=str(complaint.channel))
        await complaint.insert()

    print(f"complaints: {count} created")

    # Run the pipeline over the seeded rows. Without this the demo opens on 60
    # complaints that all say "analysis pending": no categories, no priorities,
    # no SLA spread and empty analytics.
    if triage:
        from app.services import rules_service, triage_service
        from app.services import triage as triage_engine

        await rules_service.seed_rules()
        await triage_engine.refresh_rules()

        done = 0
        for complaint in await Complaint.find_all().to_list():
            await triage_service.triage_complaint(complaint)
            done += 1
            if done % 20 == 0:
                print(f"  triaged {done}/{count}")
        print(f"triage: {done} complaints analysed")

    print(f"\nSign in at {settings.frontend_url} — admin@rakib.tn / {DEMO_PASSWORD}")
    await db.close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Rakib demo dataset")
    parser.add_argument("--force", action="store_true", help="wipe and reseed")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument(
        "--no-triage", dest="triage", action="store_false",
        help="skip running the pipeline over the seeded complaints",
    )
    asyncio.run(main(**vars(parser.parse_args())))
