import 'package:flutter/material.dart';

class AcademyScreen extends StatefulWidget {
  const AcademyScreen({Key? key}) : super(key: key);

  @override
  State<AcademyScreen> createState() => _AcademyScreenState();
}

class _AcademyScreenState extends State<AcademyScreen> {
  final List<Map<String, String>> _lessons = [
    {
      'title': 'كيف تستخدم VisionTrader AI',
      'content':
          'تعلم كيفية بدء تحليل الأسواق، رفع الصور، واستخدام النتائج لاتخاذ قرارات سريعة ومدعومة بالبيانات.',
    },
    {
      'title': 'فهم نظام التصويت والعناقيد',
      'content':
          'اكتشف كيف تعمل عناقيد القوة والهندسة والزخم في تقييم الفرص السوقية وكيف تؤثر على توصيات النظام.',
    },
    {
      'title': 'كيف تقرأ نتيجة التحليل',
      'content':
          'تعرّف على التوصية، مستوى الثقة، نقاط الدخول، الوقف، الأهداف، وكيفية الربط بين السيناريوهات المختلفة.',
    },
    {
      'title': 'استراتيجيات التداول المدعومة',
      'content':
          'مراجعة الاستراتيجيات الأكثر استخداماً، متى تعمل بشكل أفضل، وكيف تختار استراتيجية مناسبة لرأس مالك.',
    },
    {
      'title': 'إدارة المخاطر وحماية رأس المال',
      'content':
          'خطوات بسيطة لحساب حجم الصفقة، تحديد الوقف، والحد من الخسائر حتى تبقى في السوق لفترة أطول.',
    },
    {
      'title': 'كيف تتعلم المنصة من تداولاتك',
      'content':
          'استخدام التغذية الراجعة من نتائج الصفقات لتعديل أوزان الاستراتيجيات وتحسين نتائج التحليل المستقبلي.',
    },
    {
      'title': 'التقويم الاقتصادي وكيف تستفيد منه',
      'content':
          'قراءة أهم الأحداث الاقتصادية وكيف تؤثر على الأسواق العالمية، مع نصائح لاستغلال الفرص وتقليل المخاطر.',
    },
    {
      'title': 'السجل النفسي وأهميته',
      'content':
          'لماذا تسجيل العواطف والملاحظات يساعد التداول، وكيف يمكن لذلك تحسين الانضباط والسيطرة على المخاطر.',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('أكاديمية VisionTrader')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView.separated(
          itemCount: _lessons.length,
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final lesson = _lessons[index];
            return ExpansionTile(
              collapsedBackgroundColor: const Color(0xFF23243A),
              backgroundColor: const Color(0xFF23243A),
              title: Text(lesson['title']!,
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold)),
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16.0, vertical: 12.0),
                  child: Text(lesson['content']!,
                      style:
                          const TextStyle(color: Colors.white70, height: 1.5)),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
