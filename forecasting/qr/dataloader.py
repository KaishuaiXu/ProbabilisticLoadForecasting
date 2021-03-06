import numpy as np
import pandas as pd
import os
from tqdm import trange
import re
from datetime import datetime
from sklearn.preprocessing import OneHotEncoder

months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# calendar series (day of week)
def get_dow(data_set, month):
    
    year = re.findall(r"\d+", data_set)[0]
    week = []
    for i in range(months[month-1]):
        week_value = datetime.strptime(year + '%02d%02d' %(month, i+1), '%Y%m%d').weekday()
        for _ in range(24):
            week.append(week_value)

    week = np.array(week)
    onehot_encoder = OneHotEncoder(sparse=False, categories='auto')
    week = onehot_encoder.fit_transform(week.reshape(-1, 1))
    return week

# calendar series (hour of day)
def get_hod(month):
    
    day = []
    for i in range(months[month-1]):
        for _ in range(24):
            day.append(_)

    day = np.array(day)
    onehot_encoder = OneHotEncoder(sparse=False, categories='auto')
    day = onehot_encoder.fit_transform(day.reshape(-1, 1))
    return day

# weather series
def get_weather(path, data_set, month):
    
    weather_48 = pd.read_csv(os.path.join(path, 'data', 'weather', f'weather_{data_set}_cleaned.csv'))['T'].values
    weather_24 = []
    for i in range(int(len(weather_48)/2)):
        weather_24.append((weather_48[i*2] + weather_48[i*2+1])/2)
    weather_24 = np.array(weather_24)

    weather = []
    for i in range(12):
        weather.append(weather_24[sum(months[:i])*24:sum(months[:i+1])*24])
    weather = weather[month-1]
    weather = (weather - np.min(weather)) / (np.max(weather) - np.min(weather))
    return weather

def get_data(path, data_set):

    attr = pd.read_csv(os.path.join(path, 'data', f'{data_set}_attr_final.csv'))
    data = []
    for i in trange(len(attr)):
        id = attr['ID'][i]
        df = pd.read_csv(os.path.join(path, 'data', f'{data_set}_monthly', f'{id}.csv'), header = None).values
        data.append(df)
    data = np.array(data)
    return data

def get_train_set_qrnn(data, week, day, lag, d):
    l = np.maximum(d * 24, lag)

    total_X = []
    total_Y = []
    for i in range(len(data[0]) - l):

        elect = np.zeros(lag + d)
        elect[:lag] = data[0, i+l-lag:i+l]

        for j in range(d):
            elect[lag+j] = np.mean(data[0, i+l-(j+1)*24:i+l-j*24])

        temp = np.zeros(lag + 1 + d)
        temp[:lag+1] = data[1, i+l-lag:i+l+1]

        for j in range(d):
            temp[lag+j+1] = np.mean(data[1, i+l-(j+1)*24:i+l-j*24])

        X = np.hstack((elect, temp, week[i+l, :], day[i+l, :]))
        Y = data[0, i+l]
        total_X.append(X)
        total_Y.append(Y)

    total_X = np.array(total_X)
    total_Y = np.array(total_Y)
    total_Y = np.tile(total_Y,(99,1))
    
    return total_X, total_Y.T

def get_test_set_qrnn(data, test, week, day, lag, d):
    l = np.maximum(d * 24, lag)
    
    data = np.hstack((data[:, -l:], test))
    week = week[-l-168:, :].copy()
    day = day[-l-168:, :].copy()

    total_X = []
    total_Y = []
    for i in range(len(data[0]) - l):

        elect = np.zeros(lag + d)
        elect[:lag] = data[0, i+l-lag:i+l]

        for j in range(d):
            elect[lag+j] = np.mean(data[0, i+l-(j+1)*24:i+l-j*24])

        temp = np.zeros(lag + 1 + d)
        temp[:lag+1] = data[1, i+l-lag:i+l+1]

        for j in range(d):
            temp[lag+j+1] = np.mean(data[1, i+l-(j+1)*24:i+l-j*24])

        X = np.hstack((elect, temp, week[i+l, :], day[i+l, :]))
        Y = data[0, i+l]
        total_X.append(X)
        total_Y.append(Y)

    total_X = np.array(total_X)
    total_Y = np.array(total_Y)
    total_Y = np.tile(total_Y,(99,1))
    
    return total_X, total_Y.T

def get_train_set_qra(data, week, day, lag, d):
    l = np.maximum(d * 24, lag)

    total_X = []
    total_Tlag = []
    total_Td = []
    total_Y = []
    for i in range(len(data[0]) - l):

        T0 = data[1, i+l]
        tmp = np.hstack((T0, T0*T0, T0*T0*T0))
        X = np.hstack((week[i+l, :], day[i+l, :], tmp))

        Tlag = []
        for j in range(lag):
            Tt = data[1, -j-1+i+l]
            tmp = np.hstack((Tt, Tt*Tt, Tt*Tt*Tt))
            Tlag.append(tmp)
        Tlag = np.array(Tlag).reshape(-1)

        Td = []
        for j in range(d):
            Tt = np.mean(data[1, i+l-(j+1)*24:i+l-j*24])
            tmp = np.hstack((Tt, Tt*Tt, Tt*Tt*Tt))
            Td.append(tmp)
        Td = np.array(Td).reshape(-1)

        Y = data[0, i+l]

        total_X.append(X)
        total_Tlag.append(Tlag)
        total_Td.append(Td)
        total_Y.append(Y)

    total_X = np.array(total_X)
    total_Tlag = np.array(total_Tlag)
    total_Td = np.array(total_Td)
    total_Y = np.array(total_Y).reshape(-1, 1)
    return total_X, total_Tlag/lag, total_Td/d, total_Y

def get_test_set_qra(data, test, week, day, lag, d):
    l = np.maximum(d * 24, lag)
    
    data = np.hstack((data[:, -l:], test))
    week = week[-l-168:, :].copy()
    day = day[-l-168:, :].copy()

    total_X = []
    total_Tlag = []
    total_Td = []
    total_Y = []
    for i in range(len(data[0]) - l):

        T0 = data[1, i+l]
        tmp = np.hstack((T0, T0*T0, T0*T0*T0))
        X = np.hstack((week[i+l, :], day[i+l, :], tmp))

        Tlag = []
        for j in range(lag):
            Tt = data[1, -j-1+i+l]
            tmp = np.hstack((Tt, Tt*Tt, Tt*Tt*Tt))
            Tlag.append(tmp)
        Tlag = np.array(Tlag).reshape(-1)

        Td = []
        for j in range(d):
            Tt = np.mean(data[1, i+l-(j+1)*24:i+l-j*24])
            tmp = np.hstack((Tt, Tt*Tt, Tt*Tt*Tt))
            Td.append(tmp)
        Td = np.array(Td).reshape(-1)

        Y = data[0, i+l]

        total_X.append(X)
        total_Tlag.append(Tlag)
        total_Td.append(Td)
        total_Y.append(Y)

    total_X = np.array(total_X)
    total_Tlag = np.array(total_Tlag)
    total_Td = np.array(total_Td)
    total_Y = np.array(total_Y).reshape(-1, 1)
    return total_X, total_Tlag/lag, total_Td/d, total_Y