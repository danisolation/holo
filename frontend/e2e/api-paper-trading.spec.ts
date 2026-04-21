import { test, expect } from '@playwright/test';

const API = 'http://localhost:8001/api/paper-trading';

test.describe('Paper Trading API — Config', () => {
  test('GET /config returns simulation config', async ({ request }) => {
    const response = await request.get(`${API}/config`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('initial_capital');
    expect(body).toHaveProperty('auto_track_enabled');
    expect(body).toHaveProperty('min_confidence_threshold');
  });

  test('PUT /config updates simulation config', async ({ request }) => {
    // Get current config first to use as non-destructive update
    const getResp = await request.get(`${API}/config`);
    expect(getResp.status()).toBe(200);
    const currentConfig = await getResp.json();

    // Update with same values (non-destructive round-trip)
    const response = await request.put(`${API}/config`, {
      data: { initial_capital: currentConfig.initial_capital },
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('initial_capital');
    expect(body.initial_capital).toBe(currentConfig.initial_capital);
  });
});

test.describe('Paper Trading API — Trades', () => {
  test('GET /trades returns trades list', async ({ request }) => {
    const response = await request.get(`${API}/trades`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('trades');
    expect(body).toHaveProperty('total');
    expect(Array.isArray(body.trades)).toBe(true);
  });

  test('GET /trades with filters returns 200', async ({ request }) => {
    const response = await request.get(`${API}/trades?direction=long&limit=10`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('trades');
    expect(body).toHaveProperty('total');
  });
});

test.describe('Paper Trading API — Analytics Summary', () => {
  test('GET /analytics/summary returns analytics', async ({ request }) => {
    const response = await request.get(`${API}/analytics/summary`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('total_trades');
    expect(body).toHaveProperty('wins');
    expect(body).toHaveProperty('losses');
    expect(body).toHaveProperty('win_rate');
    expect(body).toHaveProperty('total_pnl');
  });
});

test.describe('Paper Trading API — Analytics Charts', () => {
  test('GET /analytics/equity-curve returns data', async ({ request }) => {
    const response = await request.get(`${API}/analytics/equity-curve`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('data');
    expect(body).toHaveProperty('initial_capital');
  });

  test('GET /analytics/drawdown returns data', async ({ request }) => {
    const response = await request.get(`${API}/analytics/drawdown`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('max_drawdown_vnd');
    expect(body).toHaveProperty('max_drawdown_pct');
    expect(body).toHaveProperty('periods');
  });

  test('GET /analytics/direction returns array', async ({ request }) => {
    const response = await request.get(`${API}/analytics/direction`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /analytics/confidence returns array', async ({ request }) => {
    const response = await request.get(`${API}/analytics/confidence`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /analytics/risk-reward returns data', async ({ request }) => {
    const response = await request.get(`${API}/analytics/risk-reward`);
    expect(response.status()).toBe(200);
  });

  test('GET /analytics/profit-factor returns data', async ({ request }) => {
    const response = await request.get(`${API}/analytics/profit-factor`);
    expect(response.status()).toBe(200);
  });

  test('GET /analytics/sector returns array', async ({ request }) => {
    const response = await request.get(`${API}/analytics/sector`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /analytics/streaks returns data', async ({ request }) => {
    const response = await request.get(`${API}/analytics/streaks`);
    expect(response.status()).toBe(200);
  });

  test('GET /analytics/timeframe returns array', async ({ request }) => {
    const response = await request.get(`${API}/analytics/timeframe`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /analytics/periodic returns array', async ({ request }) => {
    const response = await request.get(`${API}/analytics/periodic`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /analytics/calendar returns array', async ({ request }) => {
    const response = await request.get(`${API}/analytics/calendar`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });
});
