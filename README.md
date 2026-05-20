# AlphaVision AI - منصة تحليل فني مؤسسية بالذكاء الاصطناعي

**AlphaVision AI** هي منصة تداول ذكية تجمع بين 34 استراتيجية تحليل فني، بما فيها 15 مدرسة مخصصة لتتبع السيولة (حيتان السوق)، وتقنيات الـ AI والـ Quant Models. تعتمد المنصة على Gemini Vision كعقل بصري للرؤية، ومحرك DeepSeek Reasoning للاستنتاج، لتوفير توصيات احترافية ذات دقة عالية مع مسح تلقائي مستمر للأسواق.

## 🌟 المميزات
- **34 استراتيجية قوية:** تشمل مدارس التحليل الكلاسيكية (SMC, Price Action, Fibonacci) والمدارس المؤسسية.
- **15 مدرسة حيتان:** تشمل VPIN Toxicity، Liquidity Heatmaps، HFT Spoofing، وغيرها.
- **ذكاء اصطناعي ثنائي (Dual AI):** استخدام `Gemini Pro Vision` لتحليل الصور، و`DeepSeek R1` للتحليل العميق وبناء القرار.
- **ماسح تلقائي (Auto Scanner):** يعمل باستمرار كل 15 دقيقة على 18 سوقاً (فوركس، سلع، مؤشرات، وعملات رقمية).
- **إدارة مخاطر:** تحديد تلقائي لحجم اللوت (Lot Size)، RRR، ومناطق الالتقاء (Confluence).

## 🚀 كيفية التشغيل محلياً (Local Development)

1. **إعداد بيئة بايثون:**
   ```bash
   cd backend
   python -m venv venv
   source venv/Scripts/activate # Windows
   pip install -r requirements.txt
   ```

2. **تشغيل الخادم (Backend):**
   ```bash
   uvicorn main:app --reload
   ```

3. **تشغيل الواجهة (Frontend):**
   - يمكنك فتح ملف `index.html` في مجلد `frontend` مباشرة باستخدام المتصفح أو أي خادم محلي (مثل Live Server في VS Code).

## 🌐 دليل النشر على الإنترنت (الاستضافة المجانية)

المنصة مصممة للعمل على خدمات مجانية بالكامل.

### 1. نشر الـ Backend على Render
1. قم برفع مستودع المشروع إلى GitHub.
2. اذهب إلى [Render.com](https://render.com) وقم بتسجيل الدخول.
3. اختر **New Web Service**، ثم حدد مستودعك من GitHub.
4. Render سيتعرف تلقائياً على ملف `render.yaml` ومجلد `backend` وملف الـ `Dockerfile`.
5. في قسم **Environment Variables** في Render، يجب إدخال المفاتيح التالية (بدون قيم افتراضية):
   - `SECRET_KEY`
   - `GEMINI_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `OPENROUTER_API_KEY`
   - `CALENDAR_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_CHAT_ID` (يمكن ضبطه إلى `6380833552` إذا كانت هذه هي الدردشة الإدارية الصحيحة)
6. سيقوم Render بتثبيت المتطلبات من `requirements.txt` وبدء التشغيل.

### 2. نشر الـ Frontend على Vercel
1. اذهب إلى [Vercel.com](https://vercel.com) وقم بتسجيل الدخول.
2. اختر **Add New Project** وحدد مستودعك.
3. كـ **Root Directory**، اختر مجلد `frontend`.
4. اترك باقي الإعدادات الافتراضية واضغط **Deploy**.
5. سيتم نشر الواجهة بنجاح بفضل ملف `vercel.json`.

## ⏰ منع السبات (Uptime Monitor)
خدمات الاستضافة المجانية (مثل Render) تدخل في وضع السبات بعد 15 دقيقة من عدم النشاط. لمنع ذلك:
1. أنشئ حساباً مجانياً في [UptimeRobot](https://uptimerobot.com).
2. قم بإضافة مراقب جديد (New Monitor) من نوع **HTTP(s)**.
3. ضع رابط فحص الصحة الخاص بالخادم: 
   `https://alphavision-backend.onrender.com/api/health`
4. اجعل فترة الفحص (Interval) كل 5 دقائق.
