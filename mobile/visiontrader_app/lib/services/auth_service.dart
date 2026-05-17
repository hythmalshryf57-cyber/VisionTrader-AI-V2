import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String _tokenKey = 'jwt_token';
  static const String _adminKey = 'is_admin';

  Future<void> login(String token, {bool isAdmin = false}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setBool(_adminKey, isAdmin);
  }

  Future<void> setAdmin(bool isAdmin) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_adminKey, isAdmin);
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_adminKey);
  }

  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey(_tokenKey);
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  Future<bool> isAdmin() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_adminKey) ?? false;
  }
}
