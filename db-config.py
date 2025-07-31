from sqlalchemy import text, create_engine
from sshtunnel import SSHTunnelForwarder

# SSH and DB Config
ssh_host = '146.190.196.138'
ssh_user = 'forge'
ssh_private_key = r'C:\Users\shakc\.ssh\forge_fresh_ed25519'

db_host = '127.0.0.1'
db_port = 3306
db_user = 'forge'
db_pass = 'cJsrNc1PLo1HDFIk1hMf'
db_name = 'easewell_staging'

# Open SSH tunnel
with SSHTunnelForwarder(
    (ssh_host, 22),
    ssh_username=ssh_user,
    ssh_private_key=ssh_private_key,
    remote_bind_address=(db_host, db_port)
) as tunnel:

    # Create SQLAlchemy connection string
    local_port = tunnel.local_bind_port
    connection_string = f"mysql+pymysql://{db_user}:{db_pass}@127.0.0.1:{local_port}/{db_name}"
    
    # Create DB engine
    engine = create_engine(connection_string)

    # Test the connection and query Austin funeral homes
    with engine.connect() as conn:
        result = conn.execute(text("SELECT NOW();"))
        for row in result:
            print("Connected! Server time is:", row[0])
        
        print("\n🔍 Searching for Austin funeral homes...")
        
        # Check funeral_homes table structure first
        print("\n📋 Funeral Homes Table Structure:")
        try:
            result = conn.execute(text("DESCRIBE funeral_homes"))
            columns = []
            for row in result:
                columns.append(row[0])
                print(f"  - {row[0]} ({row[1]})")
        except Exception as e:
            print(f"Error describing table: {e}")
        
        # Search for Austin funeral homes
        austin_queries = [
            "SELECT fh.id, fh.name FROM funeral_homes fh WHERE fh.name LIKE '%Austin%' LIMIT 10",
            """SELECT fh.id, fh.name, a.locality, a.state 
               FROM funeral_homes fh 
               JOIN addresses a ON fh.address_id = a.id 
               WHERE a.locality LIKE '%Austin%' 
               LIMIT 10""",
            """SELECT fh.id, fh.name, a.locality, a.state 
               FROM funeral_homes fh 
               JOIN addresses a ON fh.address_id = a.id 
               WHERE a.state LIKE '%TX%' OR a.state LIKE '%Texas%' 
               LIMIT 10"""
        ]
        
        for i, query in enumerate(austin_queries, 1):
            try:
                print(f"\n📊 Query {i}: {query}")
                result = conn.execute(text(query))
                rows = result.fetchall()
                
                if rows:
                    print(f"  ✅ Found {len(rows)} results:")
                    for row in rows:
                        if len(row) > 2:
                            print(f"    ID: {row[0]}, Name: {row[1]}, City: {row[2]}, State: {row[3]}")
                        else:
                            print(f"    ID: {row[0]}, Name: {row[1]}")
                else:
                    print("  ❌ No results found")
                    
            except Exception as e:
                print(f"  ⚠️ Query failed: {e}")
        
        # Get total count and some examples
        print("\n📊 Database Statistics:")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM funeral_homes"))
            total_count = result.fetchone()[0]
            print(f"  Total funeral homes: {total_count}")
            
            # Get some examples from different cities
            result = conn.execute(text("""
                SELECT fh.id, fh.name, a.locality, a.state 
                FROM funeral_homes fh 
                LEFT JOIN addresses a ON fh.address_id = a.id 
                LIMIT 15
            """))
            examples = result.fetchall()
            print(f"\n  📋 Sample funeral homes:")
            for ex in examples:
                print(f"    ID: {ex[0]}, Name: {ex[1]}")
                if len(ex) > 2 and ex[2]:
                    print(f"      Location: {ex[2]}, {ex[3]}")
                print("    ---")
                
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
