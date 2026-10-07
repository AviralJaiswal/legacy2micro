// Prodapt ModernizeAI — LocalDB (localStorage) data layer — no seed data

const DB_KEY = 'prodapt_modernizeai_db';

const LocalDB = {
  data: null,

  init() {
    const stored = localStorage.getItem(DB_KEY);
    if (stored) {
      this.data = JSON.parse(stored);
    } else {
      this.data = {
        project: { name: '', version: '', stack: '', repo: '', health: 0, healthLabel: 'Not set' },
        stats: { totalFiles: 0, totalFilesDelta: '', dependencies: 0, dependenciesDelta: '', approved: 0, approvedDelta: '', contextsRemaining: 0, contextsRemainingSuffix: '%', contextsRemainingDelta: '' },
        projects: [],
        progress: { scope: '', codeAnalysis: { label: '', value: '', pct: 0, bar: 'bar-blue' }, archReview: { label: '', value: '', pct: 0, bar: 'bar-purple' }, aiMigration: { label: '', value: '', pct: 0, bar: 'bar-green' }, validation: { label: '', value: '', pct: 0, bar: 'bar-amber' } },
        activity: [],
        sync: { title: '', meta: '' },
        upload: { projectName: '', sourceStack: '', targetArch: '', repo: '', batchSize: '', workers: '', depth: '', retries: '', incremental: false, files: [] },
        codeAnalysis: { stats: [], selectedClass: { name: '', file: '', tags: [], deps: [], reflections: [] } },
        architecture: { stats: [], modules: [], services: [], boundaries: [] },
        scope: { assistant: [], header: { title: '', sub: '', files: '', deps: '', loc: '' }, included: [], excluded: [], unresolved: [], summary: '', target: '', risk: '', cta: '' },
        workspace: { steps: [], pct: '', time: '', filename: '', explanation: '', spIsolation: '', eventContract: '', logs: [], errorTitle: '', errorText: '' },
        validation: { stats: [], tests: [], behavioral: '', perf: [], issues: [], approve: { title: '', text: '', primary: '' } },
        reports: { stats: [], inventory: [], remaining: { total: 0, pct: 0, label: '', rows: [] }, reports: [], history: [] },
      };
      this.save();
    }
  },

  save() {
    localStorage.setItem(DB_KEY, JSON.stringify(this.data));
  },

  get(key) {
    return this.data[key];
  },

  set(key, value) {
    this.data[key] = value;
    this.save();
  },

  reset() {
    localStorage.removeItem(DB_KEY);
    this.init();
  },

  addActivity(item) {
    this.data.activity.unshift(item);
    if (this.data.activity.length > 4) this.data.activity.pop();
    this.save();
  },

  updateProject(id, updates) {
    const idx = this.data.projects.findIndex((p) => p.id === id);
    if (idx !== -1) {
      Object.assign(this.data.projects[idx], updates);
      this.save();
    }
  },

  deleteProject(id) {
    this.data.projects = this.data.projects.filter((p) => p.id !== id);
    this.save();
  },

  addProject(project) {
    project.id = 'p' + Date.now();
    this.data.projects.push(project);
    this.save();
  },
};

LocalDB.init();
