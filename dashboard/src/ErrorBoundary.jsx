import React from 'react';

/**
 * Simple error boundary — catches any uncaught render errors in child
 * components and displays a recovery UI instead of a blank screen.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Surface to console so operators can see it in devtools / logs
    console.error('Dashboard render error:', error, info);
    this.setState({ info });
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: 24, background: '#1a1a1a', color: '#f0f6fc',
          fontFamily: 'monospace', minHeight: '100vh',
        }}>
          <h2 style={{ color: '#f85149' }}>⚠ Dashboard crashed</h2>
          <p>{String(this.state.error?.message || this.state.error)}</p>
          <button
            onClick={() => this.setState({ error: null, info: null })}
            style={{
              padding: '8px 16px', background: '#238636', color: '#fff',
              border: 'none', borderRadius: 4, cursor: 'pointer', marginTop: 12,
            }}
          >
            Retry
          </button>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 16px', background: '#30363d', color: '#fff',
              border: 'none', borderRadius: 4, cursor: 'pointer',
              marginLeft: 8, marginTop: 12,
            }}
          >
            Reload page
          </button>
          {this.state.info && (
            <pre style={{
              marginTop: 16, padding: 12, background: '#0d1117',
              overflow: 'auto', maxHeight: 400, fontSize: 11,
            }}>
              {this.state.info.componentStack}
            </pre>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
