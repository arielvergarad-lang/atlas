import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

const question = z
	.object({
		q: z.string(),
		options: z.array(z.string()).min(2),
		answer: z.number().int().min(0),
		why: z.string().optional(),
	})
	.refine((x) => x.answer < x.options.length, { message: 'answer fuera de rango de options' });

export const collections = {
	docs: defineCollection({
		loader: docsLoader(),
		schema: docsSchema({
			extend: z.object({
				// Una página con `lesson` es una lección: muestra checkpoints y cuenta en el progreso.
				// `id` es el mismo en todos los idiomas, así el progreso no depende del idioma.
				lesson: z.object({ id: z.string(), guide: z.string(), order: z.number() }).optional(),
				quiz: z.array(question).optional(),
			}),
		}),
	}),
};
