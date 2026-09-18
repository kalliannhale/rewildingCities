from canopy import vocabulary as vocab

v = vocab.Vocabulary.load("seeds/schemas")

form = v.get_format("land_surface_temperature")
print(form)