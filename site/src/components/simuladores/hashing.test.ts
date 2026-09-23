// Ejecutar: node src/components/simuladores/hashing.test.ts  (Node 22.18+ corre TypeScript directo)
import assert from 'node:assert/strict';
import { anillo, asignarAnillo, asignarModulo, movidas } from './hashing.ts';

const claves = Array.from({ length: 2000 }, (_, i) => `clave:${i}`);
const tres = ['A', 'B', 'C'];
const cuatro = ['A', 'B', 'C', 'D'];
const frac = (a: string[], b: string[]) => movidas(a, b) / claves.length;

// hash % N: al pasar de 3 a 4 servidores se mueve cerca de 3/4 de las claves
const mod = frac(asignarModulo(claves, tres), asignarModulo(claves, cuatro));
assert.ok(Math.abs(mod - 0.75) < 0.05, `módulo movió ${mod}`);

// anillo con nodos virtuales: se mueve cerca de 1/4, y todo lo que se mueve va al servidor nuevo
const antes = asignarAnillo(claves, anillo(tres, 100));
const despues = asignarAnillo(claves, anillo(cuatro, 100));
const ani = frac(antes, despues);
assert.ok(Math.abs(ani - 0.25) < 0.06, `anillo movió ${ani}`);
assert.ok(antes.every((s, i) => s === despues[i] || despues[i] === 'D'), 'una clave se movió entre servidores viejos');

// quitar un servidor solo mueve las claves que tenía ese servidor
const sinB = asignarAnillo(claves, anillo(['A', 'C'], 100));
assert.ok(antes.every((s, i) => s === 'B' || s === sinB[i]), 'quitar B movió claves de otro servidor');

// más nodos virtuales = carga más pareja
const desbalance = (v: number) => {
	const cuenta = new Map<string, number>();
	for (const s of asignarAnillo(claves, anillo(cuatro, v))) cuenta.set(s, (cuenta.get(s) ?? 0) + 1);
	return Math.max(...cuenta.values()) / (claves.length / 4);
};
assert.ok(desbalance(100) < 1.25, `con 100 virtuales el más cargado tiene ${desbalance(100)}x el promedio`);
assert.ok(desbalance(1) > desbalance(100), 'los nodos virtuales no mejoraron el balance');

console.log(`ok · módulo movió ${(mod * 100).toFixed(1)}% · anillo movió ${(ani * 100).toFixed(1)}% · desbalance v=1: ${desbalance(1).toFixed(2)}x, v=100: ${desbalance(100).toFixed(2)}x`);
