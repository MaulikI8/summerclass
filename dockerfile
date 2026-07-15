# Use the official Node.js alpine image for a lightweight build
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (if available) first
COPY package*.json ./

# Install project dependencies
# Note: Use 'npm ci' instead of 'npm install' in production for clean, reproducible builds
RUN npm install

# Copy the rest of the application source code
COPY . .

# Expose the port the app runs on (default Node.js port is often 3000)
EXPOSE 3000

# Define the command to run the application
CMD [ "npm", "start" ]
