# DistributedCache

A distributed caching system that helps store and retrieve data quickly across multiple servers.

## What is This?

Imagine you have a library with thousands of books. Instead of going to the main library every time you need a book, you keep your favorite books on a shelf at home. That's what a cache does - it keeps frequently used data nearby so you can access it faster.

DistriCache takes this idea further by spreading the cache across multiple computers, making it even faster and more reliable.

## Key Features

- **Fast Data Access**: Get your data in milliseconds instead of seconds
- **Multiple Servers**: Spread data across several cache servers for better performance
- **Automatic Expiration**: Data automatically disappears after a set time (like sticky notes that fade away)
- **Smart Distribution**: Uses consistent hashing to decide which server stores which data
- **Backup Storage**: All data is saved in a database as a backup
- **Live Dashboard**: See what's happening in real-time with a web interface
- **Network Partition Simulation**: Test what happens when servers can't talk to each other

## How It Works

1. **Write Data**: When you save something, it goes to both the cache and the database
2. **Read Data**: When you need something, it checks the cache first (fast), then the database (slower)
3. **Expiration**: Data in the cache expires after a set time to keep things fresh
4. **Distribution**: Each piece of data is stored on one of several cache servers

## Dashboard Features

The web dashboard shows:

- **Control Panel**: Add or remove servers, save and get data
- **Ring Visualization**: See how data is distributed across servers
- **Metrics Chart**: View cache performance over time
- **Live Expiry Tracker**: Watch data expire in real-time
- **Log Terminal**: See what's happening in the system
- **Network Partition Mode**: Click any two servers to simulate connection failures

## Network Partitions

A network partition is when two servers can't communicate with each other, like two phones with no signal.

When you create a partition between two servers:
- The system continues working (stays available)
- Data can't be copied to both servers (loses consistency)
- You can see which server didn't get the data (red X marker)
- This demonstrates the CAP theorem in distributed systems

To test:
1. Click any server on the ring (turns yellow)
2. Click another server (creates a red lightning bolt between them)
3. Save some data and watch what happens
4. Click the lightning bolt again to restore the connection

## Time-To-Live (TTL)

TTL means how long data stays in the cache before it expires.

Think of it like a timer on a sticky note. You write something down, and after 30 seconds, the note automatically disappears. This keeps the cache fresh and removes old data you don't need anymore.

## How Data is Distributed

The system uses "consistent hashing" to decide which server stores which data:

1. Each server is assigned a position on a circle (0 to 360 degrees)
2. Each piece of data is also assigned a position on the circle
3. Data is stored on the nearest server in a clockwise direction
4. When servers are added or removed, only some data needs to move

This keeps data evenly distributed across all servers.

## Example Use Case

Online Shopping Cart:
- Store user shopping carts in the cache with 30-minute TTL
- If user is inactive for 30 minutes, cart data expires
- If user comes back, cart loads instantly from cache
- All cart data is backed up in database

Session Management:
- Store user login sessions with 1-hour TTL
- Fast session validation without database queries
- Automatic logout after inactivity
- Scales across multiple servers

## What You'll Learn

By exploring this project, you'll see:

- How distributed systems handle data across multiple servers
- What happens when servers can't communicate (CAP theorem)
- How consistent hashing distributes data evenly
- Why caches make applications faster
- How data expiration keeps systems efficient

## Running Tests

The test suite includes:

- Cache operations (get, put, delete)
- TTL and expiration
- Hash ring distribution
- Database operations
- Multiple server integration

Run with: `test.bat`

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome. Please fork the repository and submit a pull request.
