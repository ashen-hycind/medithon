const API_BASE = '/api';

export const apiService = {
  // Check backend service health
  async checkHealth() {
    try {
      const res = await fetch('/health');
      if (!res.ok) throw new Error('Health check failed');
      return await res.json();
    } catch (err) {
      console.warn('Backend server may be offline or unreachable:', err.message);
      return { status: 'offline', error: err.message };
    }
  },

  // Authenticate user status
  async getUserStatus(token) {
    const res = await fetch(`${API_BASE}/users/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(err.detail || 'Authentication failed');
    }
    return await res.json();
  },

  // Fetch user health profile
  async getProfile(token) {
    const res = await fetch(`${API_BASE}/users/profile`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch profile' }));
      throw new Error(err.detail || 'Failed to fetch profile');
    }
    return await res.json();
  },

  // Create user health profile
  async createProfile(token, profileData) {
    const res = await fetch(`${API_BASE}/users/profile`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(profileData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create profile' }));
      throw new Error(err.detail || 'Failed to create profile');
    }
    return await res.json();
  },
};
