export const fr = {
  brand: 'Rakib',
  'academic.notice': "Projet de fin d'études — plateforme de démonstration, sans affiliation officielle. Aucune réclamation déposée ici n'est traitée par la banque.",
  brandSubtitle: 'Service Réclamations',
  brandTagline: 'Gestion des réclamations',

  // ---- portal -------------------------------------------------------------
  'portal.title': 'Déposer une réclamation',
  'portal.lead':
    'Décrivez votre problème. Vous recevrez une référence et un lien de suivi personnel.',
  'portal.subject': 'Objet',
  'portal.subjectHint': 'En quelques mots',
  'portal.body': 'Votre réclamation',
  'portal.bodyHint':
    'Ce qui s’est passé, depuis quand, et ce que vous attendez. Écrivez en français, en arabe ou en derja.',
  'portal.name': 'Nom et prénom',
  'portal.email': 'Email',
  'portal.phone': 'Téléphone',
  'portal.contactHint':
    'Un email ou un téléphone suffit. Sans email, conservez le lien de suivi affiche après l envoi.',
  'portal.externalId': 'N° de compte ou référence client',
  'portal.optional': 'facultatif',
  'portal.submit': 'Envoyer la réclamation',
  'portal.submitting': 'Envoi en cours...',
  'portal.track': 'Suivre une réclamation',
  'portal.received': 'Réclamation enregistrée',
  'portal.receivedLead':
    'Votre réclamation a bien été reçue et transmise au service concerne.',
  'portal.yourRef': 'Votre référence',
  'portal.keepLink': 'Conservez ce lien',
  'portal.keepLinkHelp':
    'Ce lien’est le seul moyen de suivre votre dossier sans créer de compte. Ajoutez-le à vos favoris.',
  'portal.copyLink': 'Copier le lien',
  'portal.copied': 'Lien copié',
  'portal.openTracking': 'Ouvrir le suivi',
  'portal.newComplaint': 'Déposer une autre réclamation',
  'portal.trackInvalid': 'Lien de suivi invalide ou expiré',
  'portal.trackInvalidHelp':
    'Vérifiez le lien reçu par email. Si le problème persiste, contactez le service client avec votre référence.',
  'portal.exchanges': 'Échanges',
  'portal.noExchanges': 'Aucun message pour l’instant.',
  'portal.noExchangesHelp':
    'Un conseiller vous répondra ici dès que votre dossier aura été examiné.',
  'portal.deposited': 'Déposée le',
  'portal.myComplaints': 'Mes réclamations',
  'portal.myComplaintsLead':
    'Toutes les réclamations déposées depuis ce compte.',
  'portal.noComplaints': 'Aucune réclamation pour le moment',
  'portal.noComplaintsHelp':
    'Les réclamations que vous déposez en étant connecte apparaissent ici. Celles envoyées sans compte restent accessibles par leur lien de suivi.',
  'portal.newOne': 'Déposer une réclamation',
  'portal.backToList': 'Retour à mes réclamations',

  // ---- auth ---------------------------------------------------------------
  'auth.signIn': 'Connexion',
  'auth.signInLead': 'Espace réservé au personnel.',
  'auth.email': 'Email',
  'auth.password': 'Mot de passe',
  'auth.submit': 'Se connecter',
  'auth.submitting': 'Connexion...',
  'auth.signOut': 'Se déconnecter',
  'auth.invalid': 'Email ou mot de passe incorrect',
  'auth.createAccount': 'Créer un compte',
  'auth.register': 'Inscription',
  'auth.registerLead':
    'Un compte vous permet de retrouver toutes vos réclamations au même endroit.',
  'auth.fullName': 'Nom et prénom',
  'auth.haveAccount': 'J’ai déjà un compte',
  'auth.backToPortal': 'Retour au dépôt de réclamation',

  // ---- shell --------------------------------------------------------------
  'nav.inbox': 'Ma file',
  'nav.users': 'Utilisateurs',
  'nav.departments': 'Départements',
  'nav.admin': 'Administration',
  'nav.theme': 'Thème',

  // ---- inbox --------------------------------------------------------------
  'inbox.title': 'File de traitement',
  'inbox.search': 'Rechercher',
  'inbox.searchPlaceholder': 'Référence, objet, contenu...',
  'inbox.status': 'Statut',
  'inbox.category': 'Catégorie',
  'inbox.all': 'Tous',
  'inbox.onlyTriage': 'À trier',
  'inbox.onlyUnassigned': 'Non affectées',
  'inbox.clear': 'Réinitialiser',
  'inbox.loadMore': 'Charger plus',
  'inbox.empty': 'Aucune réclamation dans cette file',
  'inbox.emptyHelp':
    'Les nouvelles réclamations arrivent ici automatiquement une fois triées. Retirez un filtre pour élargir la recherche.',
  'inbox.emptyFiltered': 'Aucun résultat pour ces filtres',
  'inbox.count': 'réclamations',

  // ---- complaint ----------------------------------------------------------
  'complaint.back': 'Retour à la file',
  'complaint.reply': 'Répondre',
  'complaint.internalNote': 'Note interne',
  'complaint.internalOnly': 'Visible par le personnel uniquement',
  'complaint.send': 'Envoyer',
  'complaint.sending': 'Envoi...',
  'complaint.resolve': 'Marquer comme résolue',
  'complaint.retriage': 'Relancer l’analyse',
  'complaint.timeline': 'Historique',
  'complaint.messages': 'Échanges',
  'complaint.unassigned': 'Non affectée',
  'complaint.changeStatus': 'Statut',
  'complaint.vip': 'VIP',

  // Timeline actions. The raw codes are machine strings; an agent reading the
  // history of a complaint should see French, not `assignment.auto`.
  'action.complaint.created': 'Réclamation déposée',
  'action.complaint.updated': 'Modification',
  'action.complaint.resolved': 'Marquée comme résolue',
  'action.triage.done': 'Analyse terminée',
  'action.triage.requested': 'Analyse relancée',
  'action.message.reply': 'Réponse envoyée',
  'action.message.internal': 'Note interne ajoutée',

  // ---- analysis panel -----------------------------------------------------
  'analysis.title': 'Analyse',
  'analysis.category': 'Catégorie',
  'analysis.alternatives': 'Autres catégories possibles',
  'analysis.needsTriage': 'Vérification humaine requise',
  'analysis.terms': 'Termes déclenchés',
  'analysis.clickToCorrect': 'cliquez pour corriger',
  'triage.no_signal': 'aucun terme reconnu',
  'triage.insufficient_evidence': 'preuve insuffisante',
  'triage.evidence_too_spread': 'preuve trop dispersée',
  'triage.margin_too_narrow': 'marge trop étroite',
  'analysis.engineVersion': 'Version',
  'analysis.engine': 'Moteur',
  'analysis.latency': 'Durée',
  'analysis.pending': 'Analyse en cours',

  // ---- common -------------------------------------------------------------
  'common.save': 'Enregistrer',
  'common.cancel': 'Annuler',
  'common.close': 'Fermer',
  'common.create': 'Créer',
  'common.error': 'Une erreur est survenue',
  'common.retry': 'Reessayer',
  'common.none': 'Aucun',

  // ---- vocabularies -------------------------------------------------------
  'status.new': 'Nouvelle',
  'status.triaged': 'Triée',
  'status.assigned': 'Affectée',
  'status.in_progress': 'En cours',
  'status.pending_claimant': 'Attente client',
  'status.resolved': 'Résolue',
  'status.closed': 'Clôturée',
  'status.rejected': 'Rejetée',

  // ---- canaux ---------------------------------------------------------------
  'channel.web': 'Web',
  'channel.email': 'Email',
  'channel.agence': 'Agence',
  'channel.phone': 'Téléphone',
  'channel.courrier': 'Courrier',

  // ---- langues détectées ----------------------------------------------------
  'lang.fr': 'Français',
  'lang.ar': 'Arabe',
  'lang.ar-tn': 'Derja',
  'lang.en': 'Anglais',
  'lang.other': 'Autre',

  // ---- affectation ----------------------------------------------------------
  'complaint.reassign': 'Réaffecter à un agent',
  'complaint.reassigned': 'Réaffectée à {name}',
  'complaint.unassignedDone': 'Affectation retirée',
  'complaint.reassignFailed': 'La réaffectation a échoué',

  // ---- catégories -----------------------------------------------------------
  'category.CARTE_BANCAIRE': 'Carte bancaire',
  'category.DAB_GAB': 'Distributeur (DAB/GAB)',
  'category.PAIEMENT_TPE_ECOMMERCE': 'Paiement TPE et e-commerce',
  'category.VIREMENT_PRELEVEMENT': 'Virement et prélèvement',
  'category.CHEQUE_EFFET': 'Chèque et effet',
  'category.COMPTE_GESTION': 'Gestion du compte',
  'category.CREDIT_FINANCEMENT': 'Crédit et financement',
  'category.FRAIS_COMMISSIONS': 'Frais et commissions',
  'category.BANQUE_DIGITALE': 'Banque digitale',
  'category.OPERATIONS_INTERNATIONALES': 'Opérations internationales',
  'category.FRAUDE_OPERATION_NON_AUTORISEE': 'Fraude / opération non autorisée',
  'category.AGENCE_QUALITE_SERVICE': 'Agence et qualité de service',
} as const

export type TranslationKey = keyof typeof fr
