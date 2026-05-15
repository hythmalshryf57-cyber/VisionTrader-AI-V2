import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_service.dart';
import '../services/auth_service.dart';
import 'result_screen.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({Key? key}) : super(key: key);

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final ImagePicker _picker = ImagePicker();
  final List<XFile?> _images = [null, null, null];
  String _market = 'ذهب';
  String _timeframe = 'سكالبينج';
  bool _isLoading = false;
  String? _error;

  final List<String> _markets = ['ذهب', 'عملات', 'مؤشرات', 'نفط'];
  final List<String> _timeframes = ['سكالبينج', 'يومي', 'سوينغ', 'استثماري'];

  Future<void> _pickImage(int index) async {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF23243A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.photo, color: Colors.white),
                title: const Text(
                  'اختر من المعرض',
                  style: TextStyle(color: Colors.white),
                ),
                onTap: () async {
                  Navigator.pop(context);
                  final file = await _picker.pickImage(
                    source: ImageSource.gallery,
                  );
                  if (file != null) {
                    setState(() => _images[index] = file);
                  }
                },
              ),
              ListTile(
                leading: const Icon(Icons.camera_alt, color: Colors.white),
                title: const Text(
                  'التقط صورة بالكاميرا',
                  style: TextStyle(color: Colors.white),
                ),
                onTap: () async {
                  Navigator.pop(context);
                  final file = await _picker.pickImage(
                    source: ImageSource.camera,
                  );
                  if (file != null) {
                    setState(() => _images[index] = file);
                  }
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _startAnalysis() async {
    if (_images.every((element) => element == null)) {
      setState(() => _error = 'يرجى رفع صورة واحدة على الأقل');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final token = await AuthService().getToken();
      if (token == null) {
        setState(() {
          _error = 'لم يتم تسجيل الدخول بعد';
          _isLoading = false;
        });
        return;
      }

      final imageData = <String>[];
      for (final image in _images) {
        if (image != null) {
          final bytes = await File(image.path).readAsBytes();
          imageData.add(base64Encode(bytes));
        }
      }

      final response = await ApiService().uploadAnalysis(token, {
        'market': _market,
        'timeframe': _timeframe,
        'images': imageData,
      });

      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ResultScreen(analysisResult: response),
        ),
      );
    } catch (e) {
      setState(() => _error = 'حدث خطأ أثناء إرسال البيانات');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Widget _buildImageButton(int index) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: ElevatedButton(
          onPressed: () => _pickImage(index),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF5B67CA),
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
          child: Text('رفع صورة ${index + 1}'),
        ),
      ),
    );
  }

  Widget _buildPreview() {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: _images.map((image) {
        return Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            color: const Color(0xFF1E202A),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white12),
          ),
          child: image != null
              ? ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.file(File(image.path), fit: BoxFit.cover),
                )
              : const Center(
                  child: Icon(Icons.image, color: Colors.white24, size: 32),
                ),
        );
      }).toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('رفع تحليل جديد'),
        backgroundColor: const Color(0xFF23243A),
      ),
      backgroundColor: const Color(0xFF181A20),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'السوق',
                style: TextStyle(color: Colors.white70, fontSize: 16),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: const Color(0xFF23243A),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: DropdownButton<String>(
                  value: _market,
                  dropdownColor: const Color(0xFF23243A),
                  underline: const SizedBox.shrink(),
                  isExpanded: true,
                  style: const TextStyle(color: Colors.white),
                  iconEnabledColor: Colors.white,
                  items: _markets
                      .map(
                        (market) => DropdownMenuItem(
                          value: market,
                          child: Text(market),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) setState(() => _market = value);
                  },
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                'حزمة الأطر الزمنية',
                style: TextStyle(color: Colors.white70, fontSize: 16),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: const Color(0xFF23243A),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: DropdownButton<String>(
                  value: _timeframe,
                  dropdownColor: const Color(0xFF23243A),
                  underline: const SizedBox.shrink(),
                  isExpanded: true,
                  style: const TextStyle(color: Colors.white),
                  iconEnabledColor: Colors.white,
                  items: _timeframes
                      .map(
                        (timeframe) => DropdownMenuItem(
                          value: timeframe,
                          child: Text(timeframe),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) setState(() => _timeframe = value);
                  },
                ),
              ),
              const SizedBox(height: 28),
              Row(children: [for (var i = 0; i < 3; i++) _buildImageButton(i)]),
              const SizedBox(height: 20),
              _buildPreview(),
              const SizedBox(height: 24),
              if (_error != null) ...[
                Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                const SizedBox(height: 16),
              ],
              ElevatedButton(
                onPressed: _isLoading ? null : _startAnalysis,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF5B67CA),
                  padding: const EdgeInsets.symmetric(vertical: 18),
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Text(
                        'ابدأ التحليل',
                        style: TextStyle(fontSize: 16),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
