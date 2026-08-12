import type { TranslationKey } from './fr'

/**
 * Arabic covers the claimant portal only.
 *
 * The console is French because that is what Tunisian operator staff actually
 * work in; translating it would be decoration nobody reads. The portal is where
 * Arabic matters, so it is complete there. Missing keys fall back to French.
 */
export const ar: Partial<Record<TranslationKey, string>> = {
  brand: 'رقيب',
  brandTagline: 'إدارة الشكاوى',

  'portal.title': 'تقديم شكوى',
  'portal.lead': 'صف مشكلتك. ستحصل على مرجع ورابط متابعة خاص بك.',
  'portal.subject': 'الموضوع',
  'portal.subjectHint': 'في بضع كلمات',
  'portal.body': 'نص الشكوى',
  'portal.bodyHint':
    'ما الذي حدث، منذ متى، وما الذي تنتظره. يمكنك الكتابة بالعربية أو بالفرنسية أو بالدارجة.',
  'portal.name': 'الاسم واللقب',
  'portal.email': 'البريد الإلكتروني',
  'portal.phone': 'رقم الهاتف',
  'portal.contactHint':
    'يكفي بريد إلكتروني أو رقم هاتف. إذا لم يكن لديك بريد، احتفظ برابط المتابعة الذي سيظهر بعد الإرسال.',
  'portal.externalId': 'رقم الخط أو المرجع',
  'portal.optional': 'اختياري',
  'portal.submit': 'إرسال الشكوى',
  'portal.submitting': 'جاري الإرسال...',
  'portal.track': 'متابعة شكوى',
  'portal.received': 'تم تسجيل الشكوى',
  'portal.receivedLead': 'تم استلام شكواكم وإحالتها إلى المصلحة المعنية.',
  'portal.yourRef': 'المرجع الخاص بكم',
  'portal.keepLink': 'احتفظوا بهذا الرابط',
  'portal.keepLinkHelp':
    'هذا الرابط هو الوسيلة الوحيدة لمتابعة ملفكم دون إنشاء حساب. أضيفوه إلى المفضلة.',
  'portal.copyLink': 'نسخ الرابط',
  'portal.copied': 'تم نسخ الرابط',
  'portal.emailSent': 'تم إرسال الرابط أيضا إلى بريدكم الإلكتروني.',
  'portal.openTracking': 'فتح المتابعة',
  'portal.newComplaint': 'تقديم شكوى أخرى',
  'portal.trackTitle': 'متابعة شكواكم',
  'portal.trackInvalid': 'رابط المتابعة غير صالح أو منتهي الصلاحية',
  'portal.trackInvalidHelp':
    'تأكدوا من الرابط المرسل إليكم. إذا استمر المشكل، اتصلوا بخدمة الحرفاء مع ذكر المرجع.',
  'portal.exchanges': 'المراسلات',
  'portal.noExchanges': 'لا توجد رسائل حاليا.',
  'portal.noExchangesHelp': 'سيرد عليكم أحد المستشارين هنا بمجرد دراسة ملفكم.',
  'portal.rate': 'تقييم المعالجة',
  'portal.rateLead': 'تمت معالجة شكواكم. كيف كانت التجربة؟',
  'portal.rateComment': 'ملاحظة',
  'portal.rateSubmit': 'إرسال التقييم',
  'portal.rateThanks': 'شكرا على ملاحظاتكم.',
  'portal.deposited': 'قُدّمت في',
  'portal.dueBy': 'الرد متوقع قبل',

  'auth.signIn': 'تسجيل الدخول',
  'auth.email': 'البريد الإلكتروني',
  'auth.password': 'كلمة السر',
  'auth.submit': 'دخول',
  'auth.register': 'إنشاء حساب',
  'auth.fullName': 'الاسم واللقب',
  'auth.haveAccount': 'لدي حساب',
  'auth.backToPortal': 'العودة إلى تقديم شكوى',

  'common.save': 'حفظ',
  'common.cancel': 'إلغاء',
  'common.close': 'إغلاق',
  'common.loading': 'جاري التحميل',
  'common.error': 'حدث خطأ',
  'common.retry': 'إعادة المحاولة',
  'common.required': 'هذا الحقل إجباري',

  'status.new': 'جديدة',
  'status.triaged': 'مصنفة',
  'status.assigned': 'مسندة',
  'status.in_progress': 'قيد المعالجة',
  'status.pending_claimant': 'في انتظار ردكم',
  'status.resolved': 'تمت معالجتها',
  'status.closed': 'مغلقة',
  'status.rejected': 'مرفوضة',

  'channel.web': 'الويب',
  'channel.phone': 'الهاتف',
  'channel.agence': 'الوكالة',
  'channel.email': 'البريد',

  'category.FACTURATION': 'الفوترة',
  'category.PAIEMENT_RECHARGE': 'الدفع والتعبئة',
  'category.RESEAU_MOBILE': 'الشبكة الجوالة',
  'category.INTERNET_FIXE': 'الأنترنت القار',
  'category.INTERVENTION_TECHNIQUE': 'التدخل الفني',
  'category.OFFRES_ABONNEMENT': 'العروض والاشتراك',
  'category.RESILIATION_PORTABILITE': 'الفسخ ونقل الرقم',
  'category.SERVICE_CLIENT_AGENCE': 'خدمة الحرفاء والوكالة',
  'category.EQUIPEMENT': 'التجهيزات',
  'category.ROAMING_INTERNATIONAL': 'التجوال والدولي',
  'category.APPLICATION_MOBILE': 'التطبيق الجوال',
}
