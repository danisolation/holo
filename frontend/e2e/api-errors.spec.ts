import { test, expect } from '@playwright/test';

const API = 'http://localhost:8001/api';

test.describe('API Error Handling — 404 Not Found', () => {
  test('Invalid ticker symbol returns 404 for prices', async ({ request }) => {
    const response = await request.get(`${API}/tickers/INVALIDXYZ123/prices`);
    expect(response.status()).toBe(404);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });

  test('Invalid ticker symbol returns 404 for analysis summary', async ({ request }) => {
    const response = await request.get(`${API}/analysis/INVALIDXYZ123/summary`);
    expect(response.status()).toBe(404);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });

  test('Invalid ticker symbol returns 404 for indicators', async ({ request }) => {
    const response = await request.get(`${API}/analysis/INVALIDXYZ123/indicators`);
    expect(response.status()).toBe(404);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });

  test('Invalid ticker symbol returns 404 for trading-signal', async ({ request }) => {
    const response = await request.get(`${API}/analysis/INVALIDXYZ123/trading-signal`);
    expect(response.status()).toBe(404);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });

  test('Non-existent paper trade ID returns 404', async ({ request }) => {
    const response = await request.get(`${API}/paper-trading/trades/99999999`);
    expect([404, 422]).toContain(response.status());
  });

  test('Non-existent API route returns 404 or 405', async ({ request }) => {
    const response = await request.get(`${API}/nonexistent-endpoint`);
    expect([404, 405]).toContain(response.status());
  });
});

test.describe('API Error Handling — 422 Validation Error', () => {
  test('Invalid PUT config body returns 422', async ({ request }) => {
    const response = await request.put(`${API}/paper-trading/config`, {
      data: { initial_capital: 'not_a_number' },
    });
    expect(response.status()).toBe(422);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });

  test('Invalid ticker prices days param returns 422', async ({ request }) => {
    const response = await request.get(`${API}/tickers/VNM/prices?days=-1`);
    expect(response.status()).toBe(422);
  });

  test('Invalid trades direction filter returns 422', async ({ request }) => {
    const response = await request.get(`${API}/paper-trading/trades?direction=invalid`);
    expect(response.status()).toBe(422);
  });
});

test.describe('API Error Handling — 400 Bad Request', () => {
  test('Invalid exchange filter returns 400', async ({ request }) => {
    const response = await request.get(`${API}/tickers?exchange=INVALID`);
    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });

  test('Invalid corporate events month format returns 400', async ({ request }) => {
    const response = await request.get(`${API}/corporate-events?month=invalid`);
    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body).toHaveProperty('detail');
  });
});
