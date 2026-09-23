// Formato de un escenario para ScrollDiagram: un sistema que cambia etapa por etapa.
// Todo lo visible está en datos; el motor solo interpola posiciones y mueve peticiones.

export type Texto = { es: string; en: string };

export type Nodo = {
	label: Texto;
	sub?: Texto;
	/** estilo visual: 'user' (píldora), 'store' (almacenamiento), 'punto' (cruce sin texto), por defecto caja */
	kind?: 'user' | 'store' | 'punto';
};

export type Etapa = {
	/** texto corto del indicador superior, ej. "Usuarios++" */
	hud: Texto;
	/** nodos visibles y dónde van. `from`: nace desde la posición de otro nodo */
	nodos: Record<string, { x: number; y: number; from?: string; sub?: Texto; dashed?: boolean }>;
	/** conexiones "a>b"; con "~" al final se dibujan punteadas (replicación, DNS) */
	aristas: string[];
	/** rutas de peticiones con su peso. 'S' = un servidor visible al azar, 'R' = una réplica */
	rutas: { camino: string[]; peso: number; tipo: 'lectura' | 'escritura' | 'estatico' | 'async' }[];
	/** milisegundos entre peticiones: baja a medida que crece el tráfico */
	cada: number;
	/** nodo que se satura en esta etapa y motiva la siguiente */
	cuello?: { nodo: string; nota: Texto };
	/** nodos que aparecen y desaparecen solos (autoescalado) */
	respiran?: string[];
};

export type Escenario = {
	viewBox: [number, number];
	nodos: Record<string, Nodo>;
	etapas: Etapa[];
	leyenda: Record<'lectura' | 'escritura' | 'estatico' | 'async', Texto>;
};
