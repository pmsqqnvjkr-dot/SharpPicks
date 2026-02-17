import { useNavigate } from 'react-router-dom';

export default function PrivacyPolicy() {
  const navigate = useNavigate();

  const Section = ({ title, children }) => (
    <div style={{ marginBottom: '28px' }}>
      <h3 style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '16px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: '10px',
      }}>{title}</h3>
      <div style={{
        fontSize: '14px',
        lineHeight: 1.8,
        color: 'var(--text-secondary)',
      }}>{children}</div>
    </div>
  );

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      padding: '20px',
    }}>
      <div style={{
        maxWidth: '640px',
        margin: '0 auto',
        padding: '40px 0',
      }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--blue-primary)',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            marginBottom: '24px',
            padding: 0,
            fontFamily: 'var(--font-sans)',
          }}
        >
          &larr; Back
        </button>

        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '28px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '8px',
        }}>Privacy Policy</h1>
        <p style={{
          fontSize: '13px',
          color: 'var(--text-tertiary)',
          marginBottom: '32px',
          fontFamily: 'var(--font-mono)',
        }}>Last updated: February 17, 2026</p>

        <Section title="1. Introduction">
          <p>SharpPicks ("we," "us," or "our") operates the SharpPicks platform accessible at app.sharppicks.ai and through our mobile applications. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our service.</p>
        </Section>

        <Section title="2. Information We Collect">
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Account Information:</strong> When you create an account, we collect your name, email address, and encrypted password.</p>
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Payment Information:</strong> Payment processing is handled by Stripe. We do not store your credit card numbers. Stripe may collect payment card details and billing information as described in their privacy policy.</p>
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Usage Data:</strong> We collect information about how you interact with the platform, including picks viewed, bets tracked, and feature usage.</p>
          <p style={{ marginBottom: '12px' }}><strong style={{ color: 'var(--text-primary)' }}>Device Information:</strong> We may collect device type, operating system, browser type, and push notification tokens for delivering notifications.</p>
          <p><strong style={{ color: 'var(--text-primary)' }}>Cookies:</strong> We use essential cookies for authentication and session management. We do not use advertising or tracking cookies.</p>
        </Section>

        <Section title="3. How We Use Your Information">
          <p>We use the information we collect to:</p>
          <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
            <li>Provide, maintain, and improve our services</li>
            <li>Process transactions and manage subscriptions</li>
            <li>Send you picks, alerts, and service notifications</li>
            <li>Send periodic emails (weekly summaries, account updates)</li>
            <li>Monitor and analyze usage patterns to improve the platform</li>
            <li>Detect and prevent fraud or abuse</li>
          </ul>
        </Section>

        <Section title="4. Data Sharing">
          <p>We do not sell, trade, or rent your personal information to third parties. We may share information with:</p>
          <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
            <li><strong style={{ color: 'var(--text-primary)' }}>Stripe:</strong> For payment processing</li>
            <li><strong style={{ color: 'var(--text-primary)' }}>Firebase (Google):</strong> For push notification delivery</li>
            <li><strong style={{ color: 'var(--text-primary)' }}>Resend:</strong> For transactional email delivery</li>
            <li><strong style={{ color: 'var(--text-primary)' }}>Legal Requirements:</strong> When required by law or to protect our rights</li>
          </ul>
        </Section>

        <Section title="5. Data Security">
          <p>We implement appropriate security measures including encrypted passwords, HTTPS everywhere, secure token-based authentication, and regular database backups. However, no method of transmission over the Internet is 100% secure.</p>
        </Section>

        <Section title="6. Data Retention">
          <p>We retain your account data for as long as your account is active. Pick history and performance records are maintained as part of our public transparency record. You may request deletion of your account by contacting support@sharppicks.ai.</p>
        </Section>

        <Section title="7. Your Rights">
          <p>You have the right to:</p>
          <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
            <li>Access and update your personal information</li>
            <li>Request deletion of your account</li>
            <li>Opt out of non-essential communications</li>
            <li>Disable push notifications through your device settings</li>
          </ul>
        </Section>

        <Section title="8. Push Notifications">
          <p>With your permission, we send push notifications for pick alerts, pass-day updates, and results. You can disable notifications at any time through your device settings or within the app.</p>
        </Section>

        <Section title="9. Children's Privacy">
          <p>SharpPicks is not intended for individuals under 18 years of age. We do not knowingly collect personal information from minors. If you are under 18, do not use this service.</p>
        </Section>

        <Section title="10. Changes to This Policy">
          <p>We may update this Privacy Policy from time to time. We will notify you of any changes by updating the "Last updated" date. Continued use of the service constitutes acceptance of the revised policy.</p>
        </Section>

        <Section title="11. Contact Us">
          <p>If you have questions about this Privacy Policy, contact us at:</p>
          <p style={{ marginTop: '8px' }}>
            <strong style={{ color: 'var(--text-primary)' }}>Email:</strong> support@sharppicks.ai<br />
            <strong style={{ color: 'var(--text-primary)' }}>Website:</strong> app.sharppicks.ai
          </p>
        </Section>

        <hr style={{ border: 'none', borderTop: '1px solid var(--stroke-subtle)', margin: '32px 0' }} />
        <p style={{
          fontSize: '12px',
          color: 'var(--text-tertiary)',
          textAlign: 'center',
        }}>SharpPicks — Discipline is the edge.</p>
      </div>
    </div>
  );
}
