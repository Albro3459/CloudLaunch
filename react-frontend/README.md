### Running React Site:

Update dependencies:
```sh
cd CloudLaunch; 
npm install
```

Run project on local:
```sh
cd react-frontend; 
npm start
````

Keep tailwind css updated while making changes:
```sh
cd react-frontend; 
npx @tailwindcss/cli -i ./src/input.css -o ./src/output.css --watch
```

---

### Deploy GitHub page:

Push changes to main or dev, then:
```sh
cd react-frontend; 
npm run deploy # Deploys to gh-pages branch
````