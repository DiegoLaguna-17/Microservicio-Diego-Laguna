import graphene
from django.db import connection
from graphql import GraphQLError
import jwt
from django.conf import settings
from datetime import datetime, timedelta

class SeguirCreadorPayload(graphene.ObjectType):
    success = graphene.Boolean(required=True)
    usuarios_idusuario = graphene.Int()
    creadores_idcreador = graphene.Int()

class HealthCheckType(graphene.ObjectType):
    status = graphene.String()
    server_time = graphene.String()

class SeguirCreadorInput(graphene.InputObjectType):
    usuarios_idusuario = graphene.Int(required=True)
    creadores_idcreador = graphene.Int(required=True)

def get_user_id_from_token(context):
    auth_header = context.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        raise GraphQLError("Token inválido o faltante")
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        raise GraphQLError("Token expirado")
    except jwt.InvalidTokenError:
        raise GraphQLError("Token inválido")

class SeguirCreador(graphene.Mutation):
    class Arguments:
        input = SeguirCreadorInput(required=True)

    Output = SeguirCreadorPayload

    @staticmethod
    def mutate(root, info, input):
        try:
            user_id = get_user_id_from_token(info.context)
            
            if not input.usuarios_idusuario or not input.creadores_idcreador:
                raise GraphQLError("Faltan campos requeridos")
            
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO backend_listaseguidos 
                    (usuarios_idusuario, creadores_idcreador)
                    VALUES (%s, %s)
                    RETURNING creadores_idcreador
                    """,
                    [input.usuarios_idusuario, input.creadores_idcreador]
                )
                cursor.fetchone()

            return SeguirCreadorPayload(
                success=True,
                usuarios_idusuario=input.usuarios_idusuario,
                creadores_idcreador=input.creadores_idcreador
            )

        except Exception as e:
            return SeguirCreadorPayload(
                success=False,
                usuarios_idusuario=None,
                creadores_idcreador=None
            )

class Query(graphene.ObjectType):
    health = graphene.Field(HealthCheckType, description="Verifica estado del servicio")
    hola = graphene.String(description="Endpoint de prueba")

    def resolve_health(self, info):
        return HealthCheckType(
            status="OPERATIONAL",
            server_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    def resolve_hola(self, info):
        return "Mundo"

class Mutation(graphene.ObjectType):
    seguir_creador = SeguirCreador.Field()

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    auto_camelcase=True
)

def generate_test_token(user_id=1, expires_in=24):
    """Genera un token JWT para pruebas manuales"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

TEST_TOKEN = generate_test_token()
print(f"\n🔑 Token de prueba (JWT):\n{TEST_TOKEN}\n")