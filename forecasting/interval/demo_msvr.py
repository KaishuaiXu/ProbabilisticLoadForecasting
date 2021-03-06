import numpy as np
import pandas as pd
import os
from tqdm import trange
import gc

from dataloader import get_train_set_msvr, get_test_set_msvr, get_data
from msvr import kernelmatrix
from msvr import msvr

def params_search(c_start, c_end, c_step, p_start, p_end, p_step, trainX, trainY, testX):

    # Parameters
    ker = 'rbf'
    epsi = 0.001
    tol = 1e-10
    min_error = float('inf')

    Cs = np.arange(c_start, c_end, c_step)
    pars = np.arange(p_start, p_end, p_step)
    best_params = np.zeros(2)
    for i in range(len(Cs)):
        for j in range(len(pars)):

            C = Cs[i]
            par = pars[j]

            # Train
            Beta = msvr(trainX, trainY, ker, C, epsi, par, tol)

            # Predict
            K = kernelmatrix('rbf', trainX, trainX, par)
            pred = np.dot(K, Beta)

            error = np.sum((pred - trainY)**2)
            if error < min_error:
                min_error = error
                
                best_params[0] = C
                best_params[1] = par

                K = kernelmatrix('rbf', testX, trainX, par)
                pred_test = np.dot(K, Beta)
                
                best_beta = Beta
                best_pred = pred_test
    
    return best_params, best_beta, best_pred

def train_model(trainX, trainY, testX):

    best_params, best_beta, best_pred = params_search(0.1, 4.7, 0.5, 1, 64, 2, trainX, trainY, testX)
    best_params, best_beta, best_pred = params_search(np.maximum(0.1, best_params[0]-0.5), best_params[0]+0.6, 0.1, np.maximum(1, best_params[1]-2), best_params[1]+3, 1, trainX, trainY, testX)

    return best_params, best_beta, best_pred


if __name__ == "__main__":

    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # methods = ['hierarchical/euclidean', 'hierarchical/cityblock', 'hierarchical/hausdorff', 'kmeans']
    methods = ['kmeans']
    # data_sets = ['Irish_2010', 'London_2013']
    data_sets = ['London_2013']

    path = os.path.abspath(os.path.join(os.getcwd()))

    for times in range(1, 11):
        for data_set in data_sets:

            data = get_data(path, data_set)

            for method in methods:
                for n_clusters in range(1, 2):
                    for month in range(1, 13):
                        
                        path_cluster = os.path.join(path, 'result', data_set, 'clustering', 'interval', method, f'n_clusters_{n_clusters}.csv')
                        clusters = pd.read_csv(path_cluster, header=None)
                        
                        series = data[:, (month-1)*2:month*2, :months[month-1]*24]
                        
                        print('times:', times, ', data_set:', data_set, ', method:', method, ', n_clusters:', n_clusters, ', month:', month, ', series shape:', series.shape)

                        total_scale = []
                        total_beta = []
                        total_params = []
                        total_pred_series = []

                        for i in range(n_clusters):

                            index = list(clusters[month-1] == i)
                            sub_series = series[index]
                            sub_series = np.sum(sub_series, axis=0)

                            # split
                            test = sub_series[:, -168:]
                            train = sub_series[:, :-168]

                            # normalize
                            scale = np.zeros(2)
                            scale[0] = np.max(train)
                            scale[1] = np.min(train)
                            total_scale.append(scale)
                            train = (train - scale[1])/(scale[0] - scale[1])
                            test = (test - scale[1])/(scale[0] - scale[1])
                            
                            # recency effect
                            lag = 24
                            d = 1
                            
                            trainX, trainY = get_train_set_msvr(train, lag, d)
                            testX, testY = get_test_set_msvr(train, test, lag, d)
                            
                            best_params, best_beta, best_pred = train_model(trainX, trainY, testX)
                            
                            total_params.append(best_params)                            
                            total_beta.append(best_beta)
                            total_pred_series.append(best_pred.T)
                            print('cluster:', i)
                            
                            del sub_series, train, test
                            gc.collect()

                        total_beta = np.array(total_beta)
                        total_params = np.array(total_params)
                        total_pred_series = np.array(total_pred_series)
                        total_scale = np.array(total_scale)

                        path_result = os.path.join(path, 'result', data_set, 'forecasting', 'msvr', f'times_{times}', method)
                        if not os.path.exists(path_result):
                            os.makedirs(path_result)
                        
                        np.save(os.path.join(path_result, f'n_clusters_{n_clusters}_month_{month}_beta.npy'), total_beta)
                        np.save(os.path.join(path_result, f'n_clusters_{n_clusters}_month_{month}_params.npy'), total_params)
                        np.save(os.path.join(path_result, f'n_clusters_{n_clusters}_month_{month}.npy'), total_pred_series)
                        np.save(os.path.join(path_result, f'n_clusters_{n_clusters}_month_{month}_scale.npy'), total_scale)

                        del series, total_pred_series, total_scale
