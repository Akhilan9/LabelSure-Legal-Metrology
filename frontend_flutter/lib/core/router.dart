import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'auth_state.dart';
import '../widgets/app_layout.dart';
import '../pages/login_page.dart';
import '../pages/dashboard_page.dart';
import '../pages/inspections_list_page.dart';
import '../pages/new_inspection_page.dart';
import '../pages/inspection_detail_page.dart';
import '../pages/field_capture_page.dart';
import '../pages/reports_page.dart';
import '../pages/rules_repository_page.dart';
import '../pages/coming_soon_page.dart';
import '../pages/inspection_center_page.dart';

GoRouter createRouter(AuthProvider auth) {
  return GoRouter(
    initialLocation: '/dashboard',
    refreshListenable: auth,
    redirect: (context, state) {
      final isLoggingIn = state.uri.path == '/login';
      final isAuth = auth.isAuthenticated;

      if (!isAuth && !isLoggingIn) {
        return '/login';
      }
      if (isAuth && isLoggingIn) {
        return '/dashboard';
      }
      if (state.uri.path == '/') {
        return '/dashboard';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      ShellRoute(
        builder: (context, state, child) => AppLayout(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (context, state) => const DashboardPage(),
          ),
          GoRoute(
            path: '/inspection-center',
            builder: (context, state) => const InspectionCenterPage(),
          ),
          GoRoute(
            path: '/inspections',
            builder: (context, state) => const InspectionsListPage(),
          ),
          GoRoute(
            path: '/inspections/new',
            builder: (context, state) {
              final draft = state.uri.queryParameters['draft'];
              return NewInspectionPage(draftId: draft);
            },
          ),
          GoRoute(
            path: '/inspections/:id',
            builder: (context, state) {
              final id = state.pathParameters['id'] ?? '';
              return InspectionDetailPage(id: id);
            },
          ),
          GoRoute(
            path: '/reports',
            builder: (context, state) => const ReportsPage(),
          ),
          GoRoute(
            path: '/field',
            builder: (context, state) => const FieldCapturePage(),
          ),
          GoRoute(
            path: '/rules',
            builder: (context, state) => const RulesRepositoryPage(),
          ),
          GoRoute(
            path: '/forbidden',
            builder: (context, state) => const ComingSoonPage(
              title: 'Access Restricted',
              forbidden: true,
            ),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      backgroundColor: const Color(0xFF090D16),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('404 - Page not found', style: TextStyle(fontSize: 22, color: Colors.white, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () => context.go('/dashboard'),
              child: const Text('Return to LabelSure'),
            ),
          ],
        ),
      ),
    ),
  );
}
