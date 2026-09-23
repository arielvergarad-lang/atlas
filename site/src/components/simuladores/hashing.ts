// Lógica del simulador de hashing: funciones puras, probadas en hashing.test.ts.

/** FNV-1a de 32 bits con mezcla final (fmix32 de MurmurHash3) para repartir bien claves parecidas. */
export function hash(s: string): number {
	let h = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		h ^= s.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	h ^= h >>> 16;
	h = Math.imul(h, 0x85ebca6b);
	h ^= h >>> 13;
	h = Math.imul(h, 0xc2b2ae35);
	h ^= h >>> 16;
	return h >>> 0;
}

/** Posición en el anillo, entre 0 y 1. */
export const posicion = (s: string) => hash(s) / 2 ** 32;

/** Reparto clásico: hash(clave) % N. */
export const asignarModulo = (claves: string[], servidores: string[]) =>
	claves.map((k) => servidores[hash(k) % servidores.length]);

export type Punto = { pos: number; servidor: string };

/** Cada servidor ocupa `virtuales` puntos del anillo. */
export const anillo = (servidores: string[], virtuales: number): Punto[] =>
	servidores
		.flatMap((s) => Array.from({ length: virtuales }, (_, v) => ({ pos: posicion(`${s}#${v}`), servidor: s })))
		.sort((a, b) => a.pos - b.pos);

/** Consistent hashing: cada clave va al primer punto del anillo en sentido horario. */
export const asignarAnillo = (claves: string[], puntos: Punto[]) =>
	claves.map((k) => {
		const p = posicion(k);
		return (puntos.find((x) => x.pos >= p) ?? puntos[0]).servidor;
	});

export const movidas = (antes: string[], despues: string[]) => antes.filter((s, i) => s !== despues[i]).length;
