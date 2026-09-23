// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	integrations: [
		starlight({
			title: 'Atlas',
			description: 'Guías de estudio de punta a punta, interactivas y gratis.',
			defaultLocale: 'root',
			locales: {
				root: { label: 'Español', lang: 'es' },
				en: { label: 'English', lang: 'en' },
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/arielvergarad-lang/atlas' }],
			components: {
				MarkdownContent: './src/components/MarkdownContent.astro',
			},
			sidebar: [
				{ label: 'Mi progreso', translations: { en: 'My progress' }, link: '/progreso/' },
				{
					label: 'Datos y SQL',
					translations: { en: 'Data & SQL' },
					items: [{ autogenerate: { directory: 'datos' } }],
				},
				{
					label: 'Diseño de sistemas',
					translations: { en: 'System design' },
					items: [{ autogenerate: { directory: 'diseno-sistemas' } }],
				},
			],
		}),
	],
});
