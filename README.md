# ACM Auto CarPlay MFi Server

خادم وسيط مفتوح المصدر ومجاني بنسبة 100% لتشغيل Apple CarPlay على شاشات سيارات BYD (Qin Plus وغيرها) بدون أي قطع أو دونجل خارجي.

---

## الميزات
* يدعم التوقيع التلقائي لشهادات وتحديات أبل (MFi Challenge / Response).
* تفعيل غير محدود ومجاني لجميع الأجهزة دون الحاجة لأي مفاتيح أو تراخيص.
* متوافق بالكامل مع معايير بروتوكول أبل iAP2 MFi Protocol Major 2.
* خفيف وسريع جداً ومبني بتقنية FastAPI و Python 3.11.

---

## طريقة الرفع على Railway مجاناً في 3 دقائق

### الخطوة 1: إنشاء حساب على Railway
1. ادخل إلى موقع [Railway.app](https://railway.app).
2. سجل دخولك باستخدام حساب **GitHub** الخاص بك.

### الخطوة 2: رفع مجلد السيرفر إلى GitHub
1. قم بإنشاء مستودع جديد (New Repository) في حسابك على GitHub، وسمّه مثلاً: `acm-carplay-server`.
2. ارفع محتويات مجلد `tm_auto_server` (الملفات: `main.py` و `requirements.txt` و `Procfile` و `Dockerfile`) إلى المستودع.

### الخطوة 3: نشر السيرفر على Railway
1. في لوحة تحكم Railway، اضغط على **+ New Project**.
2. اختر **Deploy from GitHub repo**.
3. اختر المستودع `acm-carplay-server` الذي قمت بإنشائه.
4. سيبدأ Railway في بناء وتشغيل السيرفر تلقائياً خلال دقيقة واحدة!

### الخطوة 4: توليد الرابط العام (Public Domain)
1. داخل مشروعك على Railway، اضغط على الخدمة (Service).
2. اذهب إلى تبويب **Settings**.
3. تحت قسم **Networking** اضغط على **Generate Domain**.
4. سيظهر لك رابط مجاني خاص بك، مثل:
   `https://acm-carplay-server-production.up.railway.app`

---

## ربط السيرفر بتطبيق شاشة السيارة

بمجرد حصولك على الرابط الخاص بك:
1. افتح ملف `strings.xml` في مسار التطبيق:
   `Traffic_app_apk\qinplus_full\res\values\strings.xml`
2. عدل السطر رقم 886 ليصبح رابطك الجديد:
   ```xml
   <string name="tm_activation_server_url">https://your-new-domain.up.railway.app</string>
   ```
3. شغّل ملف البناء `scripts\build_acm_apk.bat`.
4. مبروك! سيتم إنتاج APK جديد خاص بك ومرتبط بسيرفرك الشخصي مدى الحياة.
