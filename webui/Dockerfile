# Use an official Node.js runtime as a parent image
FROM node:lts-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of your application's code
COPY . .

# Build your Next.js application
# RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Command to run your app
CMD ["npm", "run", "dev"]
