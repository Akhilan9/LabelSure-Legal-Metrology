import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_client.dart';

class User {
  final String id;
  final String email;
  final String fullName;
  final String role;
  final bool isActive;

  User({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.isActive,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? 'Legal Officer',
      role: json['role']?.toString() ?? 'INSPECTOR',
      isActive: json['is_active'] == true,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'full_name': fullName,
        'role': role,
        'is_active': isActive,
      };
}

class AuthProvider with ChangeNotifier {
  final ApiClient _api = ApiClient();
  static const String _sessionKey = 'labelsure.session';

  User? _user;
  String? _token;
  bool _isLoading = true;
  String? _sessionError;
  Timer? _expiryTimer;

  User? get user => _user;
  String? get token => _token;
  bool get isLoading => _isLoading;
  String? get sessionError => _sessionError;
  bool get isAuthenticated => _user != null && _token != null;

  AuthProvider() {
    _api.onUnauthorized = () {
      logout(message: 'Your session expired. Please sign in again.');
    };
    init();
  }

  Future<void> init() async {
    _isLoading = true;
    notifyListeners();
    await _loadSession();
    _isLoading = false;
    notifyListeners();
  }

  Future<void> _loadSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final rawSession = prefs.getString(_sessionKey);
      if (rawSession == null) return;

      final session = jsonDecode(rawSession) as Map<String, dynamic>;
      final token = session['token'] as String?;
      final expiresAt = session['expiresAt'] as int?;

      if (token == null || expiresAt == null || expiresAt <= DateTime.now().millisecondsSinceEpoch) {
        await prefs.remove(_sessionKey);
        return;
      }

      _token = token;
      _api.setAccessToken(token);

      // Verify session via /auth/me
      try {
        final data = await _api.get('/auth/me');
        if (data is Map<String, dynamic>) {
          _user = User.fromJson(data);
          _sessionError = null;

          final remainingMs = expiresAt - DateTime.now().millisecondsSinceEpoch;
          _scheduleExpiryTimer(remainingMs);
        }
      } catch (_) {
        await logout(message: 'Unable to verify your session. Please sign in again.');
      }
    } catch (_) {
      // Failed to load session
    }
  }

  void _scheduleExpiryTimer(int remainingMs) {
    _expiryTimer?.cancel();
    if (remainingMs > 0) {
      _expiryTimer = Timer(Duration(milliseconds: remainingMs), () {
        logout(message: 'Your session expired. Please sign in again.');
      });
    }
  }

  Future<void> login(String email, String password) async {
    _sessionError = null;
    final response = await _api.post('/auth/login', body: {
      'email': email.trim(),
      'password': password,
    });

    if (response is Map<String, dynamic>) {
      final token = response['access_token'] as String;
      final expiresIn = response['expires_in'] as int? ?? 86400;
      final expiresAt = DateTime.now().millisecondsSinceEpoch + (expiresIn * 1000);

      _token = token;
      _api.setAccessToken(token);

      if (response['user'] is Map<String, dynamic>) {
        _user = User.fromJson(response['user'] as Map<String, dynamic>);
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_sessionKey, jsonEncode({
        'token': token,
        'expiresAt': expiresAt,
      }));

      _scheduleExpiryTimer(expiresIn * 1000);
      notifyListeners();
    }
  }

  Future<void> logout({String? message}) async {
    _expiryTimer?.cancel();
    _token = null;
    _user = null;
    _api.setAccessToken(null);
    _sessionError = message;

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_sessionKey);
    } catch (_) {}

    notifyListeners();
  }
}
