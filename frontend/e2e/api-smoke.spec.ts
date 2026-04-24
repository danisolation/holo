import { test, expect } from '@playwright/test';

const API = 'http://localhost:8001/api';

test.describe('API Smoke Tests — Health', () => {
  test('GET /api/health returns 200 with status', async ({ request }) => {
    const response = await request.get(`${API}/health`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('status');
    expect(body).toHaveProperty('database');
    expect(body).toHaveProperty('scheduler');
    expect(body).toHaveProperty('timestamp');
  });

  test('GET /api/health/jobs returns 200', async ({ request }) => {
    const response = await request.get(`${API}/health/jobs`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('jobs');
  });

  test('GET /api/health/data-freshness returns 200', async ({ request }) => {
    const response = await request.get(`${API}/health/data-freshness`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('items');
  });

  test('GET /api/health/db-pool returns 200', async ({ request }) => {
    const response = await request.get(`${API}/health/db-pool`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('pool_size');
    expect(body).toHaveProperty('checked_in');
    expect(body).toHaveProperty('checked_out');
  });

  test('GET /api/health/summary returns 200 with status', async ({ request }) => {
    const response = await request.get(`${API}/health/summary`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('status');
    expect(body).toHaveProperty('jobs_total');
  });

  test('GET /api/health/pipeline-timeline returns 200', async ({ request }) => {
    const response = await request.get(`${API}/health/pipeline-timeline`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('runs');
  });

  test('GET /api/health/gemini-usage returns 200', async ({ request }) => {
    const response = await request.get(`${API}/health/gemini-usage`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('today');
    expect(body).toHaveProperty('daily');
  });
});

test.describe('API Smoke Tests — Tickers', () => {
  test('GET /api/tickers returns 200 with array', async ({ request }) => {
    const response = await request.get(`${API}/tickers`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      expect(body[0]).toHaveProperty('symbol');
      expect(body[0]).toHaveProperty('name');
    }
  });

  test('GET /api/tickers/{symbol}/prices returns 200 with array', async ({ request }) => {
    const response = await request.get(`${API}/tickers/VNM/prices`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      expect(body[0]).toHaveProperty('date');
      expect(body[0]).toHaveProperty('close');
      expect(body[0]).toHaveProperty('volume');
    }
  });

  test('GET /api/tickers/market-overview returns 200 with array', async ({ request }) => {
    const response = await request.get(`${API}/tickers/market-overview`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
    if (body.length > 0) {
      expect(body[0]).toHaveProperty('symbol');
      expect(body[0]).toHaveProperty('last_price');
    }
  });
});

test.describe('API Smoke Tests — Analysis', () => {
  test('GET /api/analysis/{symbol}/summary returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/summary`);
    // May be 200 or 404 if no analysis data exists — both are valid
    expect([200, 404]).toContain(response.status());
    if (response.status() === 200) {
      const body = await response.json();
      expect(body).toHaveProperty('ticker_symbol');
    }
  });

  test('GET /api/analysis/{symbol}/indicators returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/indicators`);
    expect([200, 404]).toContain(response.status());
    if (response.status() === 200) {
      const body = await response.json();
      expect(Array.isArray(body)).toBe(true);
    }
  });

  test('GET /api/analysis/{symbol}/trading-signal returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/trading-signal`);
    expect([200, 404]).toContain(response.status());
    if (response.status() === 200) {
      const body = await response.json();
      expect(body).toHaveProperty('analysis_type');
    }
  });

  test('GET /api/analysis/{symbol}/technical returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/technical`);
    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/analysis/{symbol}/fundamental returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/fundamental`);
    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/analysis/{symbol}/sentiment returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/sentiment`);
    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/analysis/{symbol}/combined returns response', async ({ request }) => {
    const response = await request.get(`${API}/analysis/VNM/combined`);
    expect([200, 404]).toContain(response.status());
  });
});
