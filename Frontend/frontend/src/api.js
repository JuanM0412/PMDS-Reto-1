const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function parseResponse(res, operationName) {
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${operationName} failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function createRun(brief) {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain: "super-app", brief }),
  });
  return parseResponse(res, "POST /runs");
}

export async function getRun(runId) {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  return parseResponse(res, `GET /runs/${runId}`);
}

export async function getAgents() {
  const res = await fetch(`${API_BASE}/agents`);
  return parseResponse(res, "GET /agents");
}

export async function approveRun(runId) {
  const res = await fetch(`${API_BASE}/runs/${runId}/approve`, {
    method: "POST",
  });
  return parseResponse(res, `POST /runs/${runId}/approve`);
}

export async function rejectRun(runId, feedback) {
  const res = await fetch(`${API_BASE}/runs/${runId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback }),
  });
  return parseResponse(res, `POST /runs/${runId}/reject`);
}

export async function getLatestArtifact(runId, artifactType) {
  const query = new URLSearchParams({ artifact_type: artifactType });
  const res = await fetch(`${API_BASE}/runs/${runId}/artifacts/latest?${query.toString()}`);
  return parseResponse(res, `GET /runs/${runId}/artifacts/latest`);
}

export async function getArtifactsExport(runId) {
  const res = await fetch(`${API_BASE}/runs/${runId}/artifacts/export`);
  return parseResponse(res, `GET /runs/${runId}/artifacts/export`);
}
