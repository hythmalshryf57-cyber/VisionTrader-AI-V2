import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/common_widgets.dart';

class AskAiScreen extends StatefulWidget {
  const AskAiScreen({Key? key}) : super(key: key);

  @override
  State<AskAiScreen> createState() => _AskAiScreenState();
}

class _AskAiScreenState extends State<AskAiScreen> {
  final _questionController = TextEditingController();
  final List<String> _suggestions = [
    'ما أفضل سوق للتداول اليوم؟',
    'قارن بين الذهب والفضة',
    'ما نسبة نجاح النظام الحالية؟',
  ];
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  bool _isLoading = false;
  String? _answer;
  String? _error;

  Future<void> _askQuestion(String question) async {
    setState(() {
      _isLoading = true;
      _error = null;
      _answer = null;
    });

    final token = await _auth.getToken();
    if (token == null) {
      setState(() {
        _error = 'يرجى تسجيل الدخول أولاً.';
        _isLoading = false;
      });
      return;
    }

    try {
      final response = await _api.askAI(token, question);
      setState(() {
        _answer = response['answer'] ??
            response['message'] ??
            'تمت معالجة السؤال بنجاح.';
      });
    } catch (e) {
      setState(() {
        _error = 'فشل الاتصال بالذكاء الاصطناعي. تحقق من الإنترنت.';
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('اسأل AI')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('اكتب سؤالك هنا',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: _questionController,
              minLines: 3,
              maxLines: 6,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'اكتب سؤالاً باللغة العربية أو الإنجليزية...',
                filled: true,
                fillColor: const Color(0xFF23243A),
                border:
                    OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _isLoading
                  ? null
                  : () => _askQuestion(_questionController.text.trim()),
              child: _isLoading
                  ? const CircularProgressIndicator()
                  : const Text('إرسال'),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _suggestions.map((suggestion) {
                return ActionChip(
                  label: Text(suggestion),
                  onPressed: () {
                    _questionController.text = suggestion;
                    _askQuestion(suggestion);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 20),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: Colors.redAccent)),
            if (_answer != null)
              GlassCard(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('رد AI',
                          style: TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 12),
                      Text(_answer!,
                          style: const TextStyle(fontSize: 16, height: 1.5)),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
