import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'widgets/common_widgets.dart';

class SettingsScreen extends StatefulWidget {
  @override
  _SettingsScreenState createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController capitalController = TextEditingController();
  double riskPercentage = 1.0;
  String? selectedRiskProfile;
  final TextEditingController telegramController = TextEditingController();

  final List<String> riskProfiles = ['محافظ', 'متوازن', 'عدواني'];

  @override
  void initState() {
    super.initState();
    loadSettings();
  }

  Future<void> loadSettings() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    setState(() {
      capitalController.text = prefs.getString('capital') ?? '';
      riskPercentage = prefs.getDouble('riskPercentage') ?? 1.0;
      selectedRiskProfile = prefs.getString('riskProfile');
      telegramController.text = prefs.getString('telegramChatId') ?? '';
    });
  }

  Future<void> saveSettings() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setString('capital', capitalController.text);
    await prefs.setDouble('riskPercentage', riskPercentage);
    await prefs.setString('riskProfile', selectedRiskProfile ?? '');
    await prefs.setString('telegramChatId', telegramController.text);
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('تم حفظ الإعدادات')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('الإعدادات')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: SingleChildScrollView(
          child: Column(
            children: [
              GlassCard(
                child: TextField(
                  controller: capitalController,
                  decoration: const InputDecoration(
                    labelText: 'رأس المال',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: Colors.white24),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: Colors.white),
                    ),
                  ),
                  style: const TextStyle(color: Colors.white),
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(height: 16),
              GlassCard(
                child: Column(
                  children: [
                    Text(
                      'نسبة المخاطرة: ${riskPercentage.toStringAsFixed(1)}%',
                      style: const TextStyle(
                          color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                    Slider(
                      value: riskPercentage,
                      min: 0.1,
                      max: 10.0,
                      divisions: 100,
                      activeColor: Colors.amber,
                      onChanged: (value) {
                        setState(() {
                          riskPercentage = value;
                        });
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GlassCard(
                child: DropdownButton<String>(
                  hint: const Text('اختر ملف المخاطرة',
                      style: TextStyle(color: Colors.white70)),
                  value: selectedRiskProfile,
                  dropdownColor: const Color(0xFF23243A),
                  style: const TextStyle(color: Colors.white),
                  onChanged: (String? newValue) {
                    setState(() {
                      selectedRiskProfile = newValue;
                    });
                  },
                  items: riskProfiles
                      .map<DropdownMenuItem<String>>((String value) {
                    return DropdownMenuItem<String>(
                      value: value,
                      child: Text(value,
                          style: const TextStyle(color: Colors.white)),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 16),
              GlassCard(
                child: TextField(
                  controller: telegramController,
                  decoration: const InputDecoration(
                    labelText: 'Telegram Chat ID',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: Colors.white24),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: Colors.white),
                    ),
                  ),
                  style: const TextStyle(color: Colors.white),
                ),
              ),
              const SizedBox(height: 16),
              PulsingButton(
                onPressed: saveSettings,
                child: const Text(
                  'حفظ',
                  style: TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
