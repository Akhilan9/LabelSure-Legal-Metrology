import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../core/auth_state.dart';
import '../core/theme.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController _emailCtrl = TextEditingController(text: 'officer@labelsure.local');
  final TextEditingController _passwordCtrl = TextEditingController(text: 'InspectorPass123!');
  bool _showPassword = false;
  bool _busy = false;
  String? _error;

  Future<void> _submit() async {
    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;

    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Enter your email address and password.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      await context.read<AuthProvider>().login(email, password);
      if (mounted) context.go('/dashboard');
    } catch (err) {
      if (mounted) {
        setState(() {
          _error = err.toString();
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 900;
    final sessionErr = context.watch<AuthProvider>().sessionError;

    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      body: isWide
          ? Row(
              children: [
                Expanded(child: _buildStoryPanel()),
                Expanded(child: Center(child: _buildLoginForm(sessionErr))),
              ],
            )
          : SingleChildScrollView(
              child: Column(
                children: [
                  _buildStoryPanel(compact: true),
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 16),
                    child: _buildLoginForm(sessionErr),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildStoryPanel({bool compact = false}) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 24 : 64, vertical: compact ? 36 : 64),
      decoration: const BoxDecoration(
        color: Color(0xFF142F36),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Brand Logo
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppTheme.emerald,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Center(
                  child: Text('L✓', style: TextStyle(color: Color(0xFF090D16), fontWeight: FontWeight.bold, fontSize: 18)),
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('LabelSure', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                  Text('APEX / SIH 26034', style: TextStyle(fontSize: 9, color: Color(0xFF94A3B8), letterSpacing: 0.8)),
                ],
              ),
            ],
          ),
          if (compact) const SizedBox(height: 32),

          // Intro
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'REGULATORY INSPECTION WORKSPACE',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFFA4BDB3), letterSpacing: 1.5),
              ),
              const SizedBox(height: 16),
              Text(
                'Inspection workspace.\nEvidence-led decisions.',
                style: GoogleFonts.playfairDisplay(
                  fontSize: compact ? 28 : 42,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFFF2F3E9),
                  height: 1.15,
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'A dedicated workspace for packaged commodity inspection, built around the people responsible for review.',
                style: TextStyle(fontSize: 13, color: Color(0xFFCADBD6), height: 1.7),
              ),
            ],
          ),
          if (compact) const SizedBox(height: 32),

          // Principle
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.only(top: 16),
                decoration: const BoxDecoration(
                  border: Border(top: BorderSide(color: Color(0xFF49615F))),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '01 / IDENTITY & ACCESS',
                      style: TextStyle(fontSize: 10, color: Color(0xFFC5AD82), letterSpacing: 1.5, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'One workspace. Verified inspectors.\nA clear boundary for every action.',
                      style: GoogleFonts.playfairDisplay(fontSize: 18, color: const Color(0xFFF2F3E9), height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                'TEAM APEX · SMART INDIA HACKATHON 2026',
                style: TextStyle(fontSize: 9, color: Color(0xFFC5AD82), letterSpacing: 1.5),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLoginForm(String? sessionErr) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 420),
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF1E293B)),
        boxShadow: const [
          BoxShadow(color: Color(0x66000000), blurRadius: 24, offset: Offset(0, 10)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0x3310B981),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'AUTHORIZED PERSONNEL',
                style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.emerald, letterSpacing: 1),
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'Sign in to LabelSure',
            style: GoogleFonts.playfairDisplay(fontSize: 26, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 4),
          const Text('Sign in with your legal inspector account.', style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
          const SizedBox(height: 20),

          // Error Alerts
          if (_error != null || sessionErr != null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0x26F43F5E),
                borderRadius: BorderRadius.circular(8),
                border: const Border(left: BorderSide(color: AppTheme.rose, width: 3)),
              ),
              child: Text(
                _error ?? sessionErr!,
                style: const TextStyle(fontSize: 11, color: Color(0xFFFECDD3)),
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Email Field
          const Text('Official email address', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.white)),
          const SizedBox(height: 6),
          TextField(
            controller: _emailCtrl,
            style: const TextStyle(fontSize: 13, color: Colors.white),
            decoration: const InputDecoration(hintText: 'name@labelsure.local'),
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 16),

          // Password Field
          const Text('Password', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.white)),
          const SizedBox(height: 6),
          TextField(
            controller: _passwordCtrl,
            obscureText: !_showPassword,
            style: const TextStyle(fontSize: 13, color: Colors.white),
            decoration: InputDecoration(
              suffixIcon: TextButton(
                onPressed: () => setState(() => _showPassword = !_showPassword),
                child: Text(
                  _showPassword ? 'Hide' : 'Show',
                  style: const TextStyle(fontSize: 11, color: AppTheme.emerald),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Submit Button
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.emerald,
              foregroundColor: const Color(0xFF090D16),
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                : const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('Sign in to workspace', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                      SizedBox(width: 8),
                      Text('↗', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ],
                  ),
          ),
          const SizedBox(height: 18),

          const Text(
            'For an account or password reset, contact your workspace administrator.',
            style: TextStyle(fontSize: 10, color: Color(0xFF64748B), height: 1.5),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          const Divider(color: Color(0xFF1E293B)),
          const SizedBox(height: 10),
          const Text(
            'LabelSure · Inspection support platform\nSIH 26034 / Team APEX prototype',
            style: TextStyle(fontSize: 9, color: Color(0xFF475569), height: 1.4),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
