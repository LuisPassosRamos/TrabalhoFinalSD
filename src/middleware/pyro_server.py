import Pyro4

@Pyro4.expose
class SensorRemote:
    def get_sensor_info(self, sensor_id):
        # Simular retorno de dados
        return {"temperatura": 24.5, "umidade": 55.2, "pressao": 1012.5}

def main():
    daemon = Pyro4.Daemon()                # Cria o daemon Pyro4
    ns = Pyro4.locateNS()                  # Localiza o servidor Name Server
    uri = daemon.register(SensorRemote)    # Registra o objeto SensorRemote
    ns.register("sensor.remote", uri)      # Registra a URI no Name Server
    print("Servidor Pyro4 rodando. URI:", uri)
    daemon.requestLoop()                   # Entra no loop de requisições

if __name__ == '__main__':
    main()
