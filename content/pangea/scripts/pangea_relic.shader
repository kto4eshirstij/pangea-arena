// Pangea Arena: skin "relic". Plain textures need no shader; sky and trim are defined here.
textures/pangea/relic/sky
{
	qer_editorimage textures/pangea/relic/sky.tga
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm sky
	q3map_sunExt 1.0 0.95 0.85 110 300 55 3 16
	q3map_skylight 70 3
	skyparms - 512 -
	{
		map textures/pangea/relic/clouds.tga
		tcMod scale 2 2
		tcMod scroll 0.012 0.006
	}
	{
		map textures/pangea/relic/clouds.tga
		blendFunc GL_ONE GL_ONE
		tcMod scale 3 3
		tcMod scroll -0.008 0.01
	}
}

textures/pangea/relic/trim_a
{
	qer_editorimage textures/pangea/relic/trim_a.tga
	q3map_surfacelight 0
	{
		map $lightmap
		rgbGen identity
	}
	{
		map textures/pangea/relic/trim_a.tga
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
}
