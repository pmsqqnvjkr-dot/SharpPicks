import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost } from '../../hooks/useApi';

export default function NotificationsScreen({ onBack }) {
  const { user, enablePush, pushStatus } = useAuth();
  const [prefs, setPrefs] = useState({
    pick_alert: true,
    no_action: true,
    outcome: true,
    weekly_summary: true,
    line_movement: true,
    journal_updates: true,
    quiet_hours_enabled: false,
    quiet_hours_start: '23:00',
    quiet_hours_end: '08:00',
    email_signals: true,
    email_results: true,
    email_weekly: true,
    email_marketing: true,
  });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [pushResult, setPushResult] = useState(null);

  useEffect(() => {
    if (user) {
      apiGet('/user/notifications').then(data => {
        if (data.prefs) setPrefs(prev => ({ ...prev, ...data.prefs }));
        setLoaded(true);
      }).catch(() => setLoaded(true));
    }
  }, [user]);

  const updatePref = async (key, value) => {
    const updated = { ...prefs, [key]: value };
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

  const togglePref = (key) => updatePref(key, !prefs[key]);

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

      <div style={{ padding: '0 20px 40px' }}>
        {!user && (
          <div style={{
            borderRadius: '12px', padding: '12px 16px', marginBottom: '12px',
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
            borderRadius: '16px', padding: '20px', marginBottom: '16px',
            border: '1px solid var(--stroke-subtle)',
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
                  backgroundColor: '#5A9E72', color: '#0A0D14',
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
                Could not enable. Your browser may not support push notifications.
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

        {/* Signal Alerts */}
        <SectionLabel text="Signal Alerts" />
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          opacity: user ? 1 : 0.6, marginBottom: '16px',
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
            label="Line movement"
            subtitle="Alerts when a watched game's line moves significantly"
            active={prefs.line_movement}
            onToggle={() => togglePref('line_movement')}
            disabled={!user}
          />
          <ToggleRow
            label="Weekly summary"
            subtitle="Weekly recap of picks, passes, and performance"
            active={prefs.weekly_summary}
            onToggle={() => togglePref('weekly_summary')}
            disabled={!user}
          />
          <ToggleRow
            label="Journal updates"
            subtitle="Notified when a new journal article is published"
            active={prefs.journal_updates}
            onToggle={() => togglePref('journal_updates')}
            disabled={!user}
            last
          />
        </div>

        {/* Quiet Hours */}
        <SectionLabel text="Quiet Hours" />
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          opacity: user ? 1 : 0.6, marginBottom: '16px',
        }}>
          <ToggleRow
            label="Quiet hours"
            subtitle="Suppress notifications during specified hours"
            active={prefs.quiet_hours_enabled}
            onToggle={() => togglePref('quiet_hours_enabled')}
            disabled={!user}
            last={!prefs.quiet_hours_enabled}
          />
          {prefs.quiet_hours_enabled && (
            <div style={{
              padding: '12px 20px 16px',
              borderTop: '1px solid var(--stroke-subtle)',
              display: 'flex', gap: '16px', alignItems: 'center',
            }}>
              <TimeInput
                label="Start"
                value={prefs.quiet_hours_start}
                onChange={(v) => updatePref('quiet_hours_start', v)}
                disabled={!user}
              />
              <span style={{ color: 'var(--text-tertiary)', fontSize: '14px' }}>to</span>
              <TimeInput
                label="End"
                value={prefs.quiet_hours_end}
                onChange={(v) => updatePref('quiet_hours_end', v)}
                disabled={!user}
              />
              <span style={{
                fontSize: '11px', color: 'var(--text-tertiary)',
                fontFamily: 'var(--font-mono)', marginLeft: 'auto',
              }}>ET</span>
            </div>
          )}
        </div>

        {/* Email Preferences */}
        <SectionLabel text="Email Notifications" />
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          opacity: user ? 1 : 0.6, marginBottom: '16px',
        }}>
          <ToggleRow
            label="Signal emails"
            subtitle="Email when a new signal is generated"
            active={prefs.email_signals}
            onToggle={() => togglePref('email_signals')}
            disabled={!user}
          />
          <ToggleRow
            label="Result emails"
            subtitle="Email when a signal outcome is graded"
            active={prefs.email_results}
            onToggle={() => togglePref('email_results')}
            disabled={!user}
          />
          <ToggleRow
            label="Weekly recap"
            subtitle="Weekly performance summary email"
            active={prefs.email_weekly}
            onToggle={() => togglePref('email_weekly')}
            disabled={!user}
          />
          <ToggleRow
            label="Market updates"
            subtitle="Daily scan results and other updates"
            active={prefs.email_marketing}
            onToggle={() => togglePref('email_marketing')}
            disabled={!user}
            last
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

function SectionLabel({ text }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
      letterSpacing: '1.5px', textTransform: 'uppercase',
      color: 'var(--text-tertiary)', padding: '8px 4px 6px',
    }}>{text}</div>
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
        backgroundColor: active ? '#5A9E72' : 'var(--surface-2)',
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

function TimeInput({ label, value, onChange, disabled }) {
  return (
    <div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        fontFamily: 'var(--font-mono)', marginBottom: '4px',
        textTransform: 'uppercase', letterSpacing: '0.5px',
      }}>{label}</div>
      <input
        type="time"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        style={{
          background: 'var(--surface-2)', border: '1px solid var(--stroke-subtle)',
          borderRadius: '8px', padding: '6px 10px',
          color: 'var(--text-primary)', fontFamily: 'var(--font-mono)',
          fontSize: '14px', colorScheme: 'dark',
        }}
      />
    </div>
  );
}
