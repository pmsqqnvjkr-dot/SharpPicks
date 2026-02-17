import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost } from '../../hooks/useApi';

export default function NotificationsScreen({ onBack }) {
  const { user, enablePush, pushStatus } = useAuth();
  const [prefs, setPrefs] = useState({
    pick_alert: true,
    no_action: false,
    outcome: true,
    weekly_summary: true,
  });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [pushResult, setPushResult] = useState(null);

  useEffect(() => {
    if (user) {
      apiGet('/user/notifications').then(data => {
        if (data.prefs) setPrefs(data.prefs);
        setLoaded(true);
      }).catch(() => setLoaded(true));
    }
  }, [user]);

  const togglePref = async (key) => {
    const updated = { ...prefs, [key]: !prefs[key] };
    setPrefs(updated);

    if (user) {
      setSaving(true);
      try {
        await apiPost('/user/notifications', { prefs: updated });
      } catch (e) {
        console.error(e);
      } finally {
        setSaving(false);
      }
    }
  };

  return (
    <div style={{ padding: '0' }}>
      <div style={{
        padding: '20px 20px 16px', display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px',
            fontWeight: 600, color: 'var(--text-primary)',
          }}>Notifications</h1>
          {saving && (
            <span style={{
              fontSize: '11px', color: 'var(--blue-primary)',
              fontFamily: 'var(--font-mono)',
            }}>Saving...</span>
          )}
        </div>
      </div>

      <div style={{ padding: '0 20px' }}>
        {!user && (
          <div style={{
            borderRadius: '12px',
            padding: '12px 16px', marginBottom: '12px',
            border: '1px solid rgba(79, 134, 247, 0.2)',
            backgroundColor: 'rgba(79, 134, 247, 0.06)',
          }}>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center' }}>
              Sign in to save your notification preferences.
            </p>
          </div>
        )}

        {user && pushStatus !== 'granted' && (
          <div style={{
            borderRadius: '16px', padding: '20px',
            marginBottom: '16px', border: '1px solid var(--stroke-subtle)',
            backgroundColor: 'var(--surface-1)', textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </div>
            <div style={{
              fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)',
              marginBottom: '4px',
            }}>Enable Push Notifications</div>
            <div style={{
              fontSize: '12px', color: 'var(--text-tertiary)',
              marginBottom: '16px', lineHeight: '1.5',
            }}>
              {pushStatus === 'denied'
                ? 'Notifications are blocked. Please enable them in your device settings.'
                : 'Get instant alerts when picks are published and results are graded.'}
            </div>
            {pushStatus !== 'denied' && (
              <button
                onClick={async () => {
                  setPushLoading(true);
                  setPushResult(null);
                  const success = await enablePush();
                  setPushLoading(false);
                  setPushResult(success ? 'enabled' : 'failed');
                }}
                disabled={pushLoading}
                style={{
                  backgroundColor: 'var(--blue-primary)', color: '#fff',
                  border: 'none', borderRadius: '10px', padding: '10px 24px',
                  fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                  opacity: pushLoading ? 0.6 : 1,
                }}
              >
                {pushLoading ? 'Enabling...' : 'Enable Notifications'}
              </button>
            )}
            {pushResult === 'enabled' && (
              <div style={{ fontSize: '12px', color: '#22C55E', marginTop: '8px' }}>
                Notifications enabled successfully
              </div>
            )}
            {pushResult === 'failed' && (
              <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '8px' }}>
                Could not enable — your browser may not support push notifications
              </div>
            )}
          </div>
        )}

        {user && pushStatus === 'granted' && (
          <div style={{
            borderRadius: '12px', padding: '12px 16px', marginBottom: '12px',
            border: '1px solid rgba(34, 197, 94, 0.2)',
            backgroundColor: 'rgba(34, 197, 94, 0.06)',
            display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span style={{ fontSize: '13px', color: '#22C55E' }}>Push notifications enabled</span>
          </div>
        )}

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          opacity: user ? 1 : 0.6,
        }}>
          <ToggleRow
            label="Pick alerts"
            subtitle="Notified when a qualifying pick is published"
            active={prefs.pick_alert}
            onToggle={() => togglePref('pick_alert')}
            disabled={!user}
          />
          <ToggleRow
            label="No-action days"
            subtitle="Notified when the model passes on all games"
            active={prefs.no_action}
            onToggle={() => togglePref('no_action')}
            disabled={!user}
          />
          <ToggleRow
            label="Outcome results"
            subtitle="Notified when a pick is graded win or loss"
            active={prefs.outcome}
            onToggle={() => togglePref('outcome')}
            disabled={!user}
          />
          <ToggleRow
            label="Weekly summary"
            subtitle="Weekly recap of picks, passes, and performance"
            active={prefs.weekly_summary}
            onToggle={() => togglePref('weekly_summary')}
            last
            disabled={!user}
          />
        </div>

        {user && (
          <p style={{
            fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '16px',
            lineHeight: '1.5', textAlign: 'center',
          }}>
            Preferences are saved automatically to your account.
          </p>
        )}
      </div>
    </div>
  );
}

function ToggleRow({ label, subtitle, active, onToggle, last, disabled }) {
  return (
    <div style={{
      padding: '16px 20px',
      borderBottom: last ? 'none' : '1px solid var(--stroke-subtle)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div>
        <div style={{
          fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
        }}>{label}</div>
        <div style={{
          fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
        }}>{subtitle}</div>
      </div>
      <button onClick={disabled ? undefined : onToggle} disabled={disabled} style={{
        width: '44px', height: '24px', borderRadius: '12px', border: 'none',
        backgroundColor: active ? 'var(--blue-primary)' : 'var(--surface-2)',
        cursor: 'pointer', position: 'relative', transition: 'background-color 0.2s',
        flexShrink: 0,
      }}>
        <div style={{
          width: '20px', height: '20px', borderRadius: '50%',
          backgroundColor: '#fff', position: 'absolute', top: '2px',
          left: active ? '22px' : '2px', transition: 'left 0.2s',
        }} />
      </button>
    </div>
  );
}
