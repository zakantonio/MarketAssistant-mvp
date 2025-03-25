FROM nginx:alpine

# Add build argument for environment
ARG ENV=production

# Copy the client files to the nginx html directory
COPY . /usr/share/nginx/html

# Copy the appropriate environment file
COPY js/env.${ENV}.js /usr/share/nginx/html/js/env.js

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]