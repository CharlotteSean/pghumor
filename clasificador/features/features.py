from __future__ import absolute_import

import features.jergasexual
import features.oov
import features.primerapersona

class Features:
	
	def __init__(self):
		self.features = [
			features.jergasexual.JergaSexual(),
			features.oov.OOV(),
			features.primerapersona.PrimeraPersona()
		]

	def calcular_features(self, tweets):
		for feature in self.features:
			for tweet in tweets:
				feature.calcular_feature(tweet)
