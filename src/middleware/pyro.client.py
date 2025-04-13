import Pyro4

def main():
    ns = Pyro4.locateNS()                        
    uri = ns.lookup("sensor.remote")             
    sensor_remote = Pyro4.Proxy(uri)
    dados = sensor_remote.get_sensor_info("sensor1")
    print("Dados do sensor remoto:", dados)

if __name__ == '__main__':
    main()
