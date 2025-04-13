import grpc
import sensor_pb2
import sensor_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = sensor_pb2_grpc.SensorServiceStub(channel)
    request = sensor_pb2.SensorRequest(sensor_id="sensor1")
    response = stub.GetSensorData(request)
    print("Dados do sensor:")
    print("Temperatura:", response.temperatura)
    print("Umidade:", response.umidade)
    print("Pressão:", response.pressao)

if __name__ == '__main__':
    run()
