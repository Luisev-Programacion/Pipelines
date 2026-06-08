from pipelines.comscore_mexico_flash.pipeline import run_pipeline as run_pipeline
from pipelines.showtime_mexico_peliculas.pipeline import run_pipeline as run_pipeline2
from pipelines.oracle_A1.pipeline import run_pipeline as run_pipeline3
from pipelines.showtime_promos.pipeline import run_pipeline as run_pipeline4

if __name__ == "__main__":
    #run_pipeline()#comscoreGrosses
    run_pipeline2()#Showtime Peliculas
    #run_pipeline3()#Oracle A1
    #run_pipeline4()#Showtime Promos