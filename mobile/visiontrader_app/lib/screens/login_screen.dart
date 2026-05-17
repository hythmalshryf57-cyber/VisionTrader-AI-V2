import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _inviteController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  void _login() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    final api = ApiService();
    final auth = AuthService();
    try {
      final res = await api.login(
        _emailController.text,
        _passwordController.text,
        _inviteController.text,
      );
      if (res['token'] != null) {
        final bool isAdminFlag =
            res['is_admin'] == true || res['admin'] == true;
        await auth.login(res['token'], isAdmin: isAdminFlag);
        Navigator.pushReplacementNamed(context, '/dashboard');
      } else {
        setState(() => _error = res['detail'] ?? 'Login failed');
      }
    } catch (e) {
      setState(() => _error = 'حدث خطأ أثناء تسجيل الدخول');
    }
    setState(() => _isLoading = false);
  }

  void _register() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    final api = ApiService();
    try {
      final res = await api.register(
        _emailController.text,
        _passwordController.text,
        _inviteController.text,
      );
      setState(() => _error = res['message'] ?? 'تم التسجيل بنجاح');
    } catch (e) {
      setState(() => _error = 'حدث خطأ أثناء التسجيل');
    }
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      backgroundColor: Color(0xFF181A20),
      body: Center(
        child: SingleChildScrollView(
          child: Container(
            padding: const EdgeInsets.all(24),
            width: 350,
            decoration: BoxDecoration(
              color: Color(0xFF23243A),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black26,
                  blurRadius: 16,
                  offset: Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'VisionTrader AI',
                  style: theme.textTheme.headline5?.copyWith(
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 24),
                TextField(
                  controller: _emailController,
                  style: TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'البريد الإلكتروني',
                    labelStyle: TextStyle(color: Colors.white70),
                    filled: true,
                    fillColor: Color(0xFF23243A),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passwordController,
                  obscureText: true,
                  style: TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'كلمة المرور',
                    labelStyle: TextStyle(color: Colors.white70),
                    filled: true,
                    fillColor: Color(0xFF23243A),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _inviteController,
                  style: TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'كود الدعوة',
                    labelStyle: TextStyle(color: Colors.white70),
                    filled: true,
                    fillColor: Color(0xFF23243A),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 24),
                if (_error != null)
                  Text(_error!, style: TextStyle(color: Colors.redAccent)),
                if (_isLoading) CircularProgressIndicator(),
                if (!_isLoading)
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          onPressed: _login,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Color(0xFF5B67CA),
                          ),
                          child: Text('دخول'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _register,
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Color(0xFF5B67CA),
                            side: BorderSide(color: Color(0xFF5B67CA)),
                          ),
                          child: Text('تسجيل'),
                        ),
                      ),
                    ],
                  ),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: () {
                    // Implement Google Sign-In
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Google Sign-In قيد التطوير')),
                    );
                  },
                  icon: Icon(Icons.g_mobiledata),
                  label: Text('تسجيل الدخول بـ Google'),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                ),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () {
                    // Open Telegram bot
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('افتح تطبيق Telegram للحصول على الرمز'),
                      ),
                    );
                  },
                  child: Text('الحصول على رمز الدعوة'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
