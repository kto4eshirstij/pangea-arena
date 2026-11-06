// Pangea Arena — skin "siberian_core" (Вэр-Кирракс: базальт, жар, иней). GPLv2.
// Рендерер OpenGL2 (веб и нативный): диффуз + normalMap + specularMap + lightmap, эмиссивные слои сверху.
// Файлы: <name>.tga диффуз, <name>_n.tga нормали (+Y вверх), <name>_s.tga спекуляр (RGB) + глянец (A), <name>_g.tga свечение.

// ---------- стены / пол / потолок ----------
textures/pangea/siberian_core/floor_a
{
	qer_editorimage textures/pangea/siberian_core/floor_a.tga
	q3map_lightmapSampleSize 8
	{
		map textures/pangea/siberian_core/floor_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/siberian_core/floor_a_n.tga
		stage normalMap
		normalScale 1.0 1.0
	}
	{
		map textures/pangea/siberian_core/floor_a_s.tga
		stage specularMap
		specularScale 0.6 0.6 0.6 0.9
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
}

textures/pangea/siberian_core/wall_a
{
	qer_editorimage textures/pangea/siberian_core/wall_a.tga
	q3map_lightmapSampleSize 8
	{
		map textures/pangea/siberian_core/wall_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/siberian_core/wall_a_n.tga
		stage normalMap
		normalScale 1.0 1.0
	}
	{
		map textures/pangea/siberian_core/wall_a_s.tga
		stage specularMap
		specularScale 0.5 0.5 0.5 0.8
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
}

textures/pangea/siberian_core/ceil_a
{
	qer_editorimage textures/pangea/siberian_core/ceil_a.tga
	q3map_lightmapSampleSize 16
	{
		map textures/pangea/siberian_core/ceil_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/siberian_core/ceil_a_n.tga
		stage normalMap
		normalScale 1.4 1.4
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
}

// ---------- ржавая окантовка с тлеющей гравировкой ----------
textures/pangea/siberian_core/trim_a
{
	qer_editorimage textures/pangea/siberian_core/trim_a.tga
	q3map_surfacelight 200
	q3map_lightimage textures/pangea/siberian_core/trim_a_g.tga
	q3map_lightsubdivide 128
	{
		map textures/pangea/siberian_core/trim_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/siberian_core/trim_a_n.tga
		stage normalMap
	}
	{
		map textures/pangea/siberian_core/trim_a_s.tga
		stage specularMap
		specularScale 0.9 0.8 0.7 1.0
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/siberian_core/trim_a_g.tga
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.75 0.25 0 0.4
	}
}

// ---------- светильник: диск солнца, излучает свет ----------
textures/pangea/siberian_core/lamp
{
	qer_editorimage textures/pangea/siberian_core/lamp.tga
	surfaceparm nomarks
	q3map_surfacelight 2800
	q3map_lightimage textures/pangea/siberian_core/lamp_g.tga
	q3map_lightsubdivide 32
	{
		map textures/pangea/siberian_core/lamp.tga
		rgbGen identity
	}
	{
		map textures/pangea/siberian_core/lamp_n.tga
		stage normalMap
	}
	{
		map textures/pangea/siberian_core/lamp_s.tga
		stage specularMap
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/siberian_core/lamp_g.tga
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.85 0.15 0 0.25
	}
}

// ---------- пол круга кулачной дуэли ----------
textures/pangea/siberian_core/ring_floor
{
	qer_editorimage textures/pangea/siberian_core/ring_floor.tga
	q3map_lightmapSampleSize 8
	{
		map textures/pangea/siberian_core/ring_floor.tga
		rgbGen identity
	}
	{
		map textures/pangea/siberian_core/ring_floor_n.tga
		stage normalMap
	}
	{
		map textures/pangea/siberian_core/ring_floor_s.tga
		stage specularMap
		specularScale 0.6 0.6 0.5 0.8
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
}

// ---------- джамп-пад: кольца бегут наружу ----------
textures/pangea/siberian_core/pad
{
	qer_editorimage textures/pangea/siberian_core/pad_base.tga
	surfaceparm nomarks
	q3map_surfacelight 300
	q3map_lightimage textures/pangea/siberian_core/pad_rings.tga
	{
		map textures/pangea/siberian_core/pad_base.tga
		rgbGen identity
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/siberian_core/pad_rings.tga
		blendFunc GL_ONE GL_ONE
		tcMod stretch sin 0.9 0.35 0 0.7
		rgbGen wave sin 0.7 0.3 0 0.7
	}
}

// ---------- телепорт: спираль ----------
textures/pangea/siberian_core/tele
{
	qer_editorimage textures/pangea/siberian_core/pad_base.tga
	surfaceparm nomarks
	q3map_surfacelight 300
	q3map_lightimage textures/pangea/siberian_core/tele_spiral.tga
	{
		map textures/pangea/siberian_core/pad_base.tga
		rgbGen identity
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/siberian_core/tele_spiral.tga
		blendFunc GL_ONE GL_ONE
		tcMod rotate 45
		rgbGen wave sin 0.8 0.2 0 0.5
	}
}

// ---------- небо ----------
textures/pangea/siberian_core/sky
{
	qer_editorimage textures/pangea/siberian_core/sky.tga
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_sunExt 1.0 0.78 0.55 95 320 18 3 16
	q3map_skylight 90 4
	skyparms textures/pangea/siberian_core/env/sky 1024 -
	{
		map textures/pangea/siberian_core/clouds.tga
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.35 0.38 )
		tcMod scale 3 3
		tcMod scroll 0.006 0.003
	}
	{
		map textures/pangea/siberian_core/clouds2.tga
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.2 0.2 0.22 )
		tcMod scale 5 5
		tcMod scroll -0.004 0.005
	}
}
