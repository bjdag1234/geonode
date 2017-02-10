from suc_rb_keywords import caller_function

# SAR DEM
print '#' * 40
print 'SAR DEM'
keyword_filter = 'sar_'
caller_function(keyword_filter)
print 'FINISHED SAR DEM'
print '#' * 40

# DEM COVERAGE
print '#' * 40
print 'DEM'
keyword_filter = 'dem_'
caller_function(keyword_filter)
print 'FINISHED DEM COVERAGE'
print '#' * 40

# COVERAGE
print '#' * 40
print 'COVERAGES'
keyword_filter = 'coverage'
caller_function(keyword_filter)
print 'FINISHED COVERAGES'
print '#' * 40

# #FHM
# print '#' * 40
# print 'FLOOD HAZARD MAPS'
# keyword_filter = '_fh'
# caller_function(keyword_filter)
# print 'FINISHED FLOOD HAZARD MAPS'
# print '#' * 40
