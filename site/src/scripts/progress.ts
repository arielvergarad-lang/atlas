// Progreso local: vive solo en el navegador de quien aprende. Sin cuenta ni servidor.
// ponytail: localStorage no viaja entre dispositivos; exportar/importar o cuenta cuando alguien lo pida.
const KEY = 'atlas:progress:v1';

export type LessonProgress = { read?: number; practiced?: number; quiz?: number };
type All = Record<string, LessonProgress>;

export function load(): All {
	try {
		return JSON.parse(localStorage.getItem(KEY) || '{}');
	} catch {
		return {};
	}
}

export function update(id: string, patch: LessonProgress): LessonProgress {
	const all = load();
	all[id] = { ...all[id], ...patch };
	try {
		localStorage.setItem(KEY, JSON.stringify(all));
	} catch {
		// modo privado o storage bloqueado: la página sigue funcionando sin guardar
	}
	return all[id];
}

export function clear() {
	try {
		localStorage.removeItem(KEY);
	} catch {}
}

export function status(p: LessonProgress | undefined, hasQuiz: boolean): 'done' | 'inProgress' | 'todo' {
	if (!p || !(p.read || p.practiced || p.quiz)) return 'todo';
	return p.read && p.practiced && (p.quiz || !hasQuiz) ? 'done' : 'inProgress';
}
