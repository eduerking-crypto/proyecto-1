/* GENOMIND — Cliente API */
"use strict";

const API = {
  base: "",
  token: null,

  async request(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(this.base + path, opts);
    } catch (e) {
      throw new Error("Sin conexión con el servidor. Ejecuta 'python run.py' en la raíz del proyecto.");
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* respuesta vacía */ }
    if (!res.ok) {
      const msg = data && data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : `Error HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  },

  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  del(path) { return this.request("DELETE", path); },

  /* Atajos */
  health() { return this.get("/api/health"); },
  agents() { return this.get("/api/meta/agents"); },
  diseases() { return this.get("/api/diseases"); },
  diseaseSnps(code) { return this.get(`/api/diseases/${code}/snps`); },
  batchPRS(payload) { return this.post("/api/analysis/polygenic/batch", payload); },
  geneEnvironment(payload) { return this.post("/api/analysis/gene-environment", payload); },
  regions() { return this.get("/api/regions"); },
  foods(params) {
    const q = new URLSearchParams(params || {}).toString();
    return this.get("/api/foods" + (q ? `?${q}` : ""));
  },
  compareFoods(ids) { return this.post("/api/foods/compare", { ids }); },
  basket(maxCost) { return this.post("/api/nutrition/basket", { max_cost: maxCost || null }); },
  stats(tool, payload) { return this.post(`/api/stats/${tool}`, payload); },
  saveProfile(p) { return this.post("/api/profiles", p); },
  listProfiles() { return this.get("/api/profiles"); },
  getProfile(id) { return this.get(`/api/profiles/${id}`); },
  deleteProfile(id) { return this.del(`/api/profiles/${id}`); },
};
