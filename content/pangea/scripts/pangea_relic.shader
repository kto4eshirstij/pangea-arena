// Pangea Arena — skin "relic" (камень + ржавый реликт). GPLv2.
// Рендерер OpenGL2 (веб и нативный): диффуз + normalMap + specularMap + lightmap, эмиссивные слои сверху.
// Файлы: <name>.tga диффуз, <name>_n.tga нормали (+Y вверх), <name>_s.tga спекуляр (RGB) + глянец (A), <name>_g.tga свечение.

// ---------- стены / пол / потолок ----------
textures/pangea/relic/floor_a
{
	qer_editorimage textures/pangea/relic/floor_a.tga
	q3map_lightmapSampleSize 8
	{
		map textures/pangea/relic/floor_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/relic/floor_a_n.tga
		stage normalMap
		normalScale 1.0 1.0
	}
	{
		map textures/pangea/relic/floor_a_s.tga
		stage specularMap
		specularScale 0.6 0.6 0.6 0.9
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
}

textures/pangea/relic/wall_a
{
	qer_editorimage textures/pangea/relic/wall_a.tga
	q3map_lightmapSampleSize 8
	{
		map textures/pangea/relic/wall_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/relic/wall_a_n.tga
		stage normalMap
		normalScale 1.0 1.0
	}
	{
		map textures/pangea/relic/wall_a_s.tga
		stage specularMap
		specularScale 0.5 0.5 0.5 0.8
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
}

textures/pangea/relic/ceil_a
{
	qer_editorimage textures/pangea/relic/ceil_a.tga
	q3map_lightmapSampleSize 16
	{
		map textures/pangea/relic/ceil_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/relic/ceil_a_n.tga
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
textures/pangea/relic/trim_a
{
	qer_editorimage textures/pangea/relic/trim_a.tga
	q3map_surfacelight 200
	q3map_lightimage textures/pangea/relic/trim_a_g.tga
	q3map_lightsubdivide 128
	{
		map textures/pangea/relic/trim_a.tga
		rgbGen identity
	}
	{
		map textures/pangea/relic/trim_a_n.tga
		stage normalMap
	}
	{
		map textures/pangea/relic/trim_a_s.tga
		stage specularMap
		specularScale 0.9 0.8 0.7 1.0
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/relic/trim_a_g.tga
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.75 0.25 0 0.4
	}
}

// ---------- светильник: диск солнца, излучает свет ----------
textures/pangea/relic/lamp
{
	qer_editorimage textures/pangea/relic/lamp.tga
	surfaceparm nomarks
	q3map_surfacelight 2800
	q3map_lightimage textures/pangea/relic/lamp_g.tga
	q3map_lightsubdivide 32
	{
		map textures/pangea/relic/lamp.tga
		rgbGen identity
	}
	{
		map textures/pangea/relic/lamp_n.tga
		stage normalMap
	}
	{
		map textures/pangea/relic/lamp_s.tga
		stage specularMap
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/relic/lamp_g.tga
		blendFunc GL_ONE GL_ONE
		rgbGen wave sin 0.85 0.15 0 0.25
	}
}

// ---------- пол круга кулачной дуэли ----------
textures/pangea/relic/ring_floor
{
	qer_editorimage textures/pangea/relic/ring_floor.tga
	q3map_lightmapSampleSize 8
	{
		map textures/pangea/relic/ring_floor.tga
		rgbGen identity
	}
	{
		map textures/pangea/relic/ring_floor_n.tga
		stage normalMap
	}
	{
		map textures/pangea/relic/ring_floor_s.tga
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
textures/pangea/relic/pad
{
	qer_editorimage textures/pangea/relic/pad_base.tga
	surfaceparm nomarks
	q3map_surfacelight 300
	q3map_lightimage textures/pangea/relic/pad_rings.tga
	{
		map textures/pangea/relic/pad_base.tga
		rgbGen identity
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/relic/pad_rings.tga
		blendFunc GL_ONE GL_ONE
		tcMod stretch sin 0.9 0.35 0 0.7
		rgbGen wave sin 0.7 0.3 0 0.7
	}
}

// ---------- телепорт: спираль ----------
textures/pangea/relic/tele
{
	qer_editorimage textures/pangea/relic/pad_base.tga
	surfaceparm nomarks
	q3map_surfacelight 300
	q3map_lightimage textures/pangea/relic/tele_spiral.tga
	{
		map textures/pangea/relic/pad_base.tga
		rgbGen identity
	}
	{
		map $lightmap
		rgbGen identity
		blendFunc filter
	}
	{
		map textures/pangea/relic/tele_spiral.tga
		blendFunc GL_ONE GL_ONE
		tcMod rotate 45
		rgbGen wave sin 0.8 0.2 0 0.5
	}
}

// ---------- небо ----------
textures/pangea/relic/sky
{
	qer_editorimage textures/pangea/relic/sky.tga
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_sunExt 1.0 0.94 0.82 120 300 55 3 16
	q3map_skylight 90 4
	skyparms textures/pangea/relic/env/sky 1024 -
	{
		map textures/pangea/relic/clouds.tga
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.35 0.35 0.38 )
		tcMod scale 3 3
		tcMod scroll 0.006 0.003
	}
	{
		map textures/pangea/relic/clouds2.tga
		blendFunc GL_ONE GL_ONE
		rgbGen const ( 0.2 0.2 0.22 )
		tcMod scale 5 5
		tcMod scroll -0.004 0.005
	}
}
