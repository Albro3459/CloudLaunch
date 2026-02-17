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

* NOTE: This uses the your local build code to deploy. It does NOT pull from any remote branch. It compiles your code to the build folder and deploys that. 
    * Pro: Can be ran from any branch
    * Con: Must be run locally and it can be confusing

Push changes to main or dev.

Then:
```sh
cd react-frontend; 
npm run deploy # Deploys to gh-pages branch
````