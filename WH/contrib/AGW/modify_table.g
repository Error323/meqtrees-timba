# glish script to copy 'PREDICT' column generated by CLAR_predict script
# to DATA and CORRECTED_DATA columns so 'imager' can make images
include 'tables.g'
t:=table("TEST_CLAR.MS",readonly=F)
predicted_data := t.getcol("PREDICT")
t.putcol("DATA", predicted_data)
t.putcol("CORRECTED_DATA", predicted_data)
t.flush()
t.close()


