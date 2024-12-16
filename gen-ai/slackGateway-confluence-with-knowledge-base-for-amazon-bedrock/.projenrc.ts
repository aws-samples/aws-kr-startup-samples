// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { awscdk, github, javascript } from "projen";

const project = new awscdk.AwsCdkTypeScriptApp({
	cdkVersion: "2.153.0",
	cdkVersionPinning: true,
	githubOptions: {
		mergify: false,
	},
	copyrightOwner: "Amazon.com, Inc. or its affiliates. All Rights Reserved.",
	license: "MIT-0",
	packageManager: javascript.NodePackageManager.NPM,
	pullRequestTemplate: true,
	pullRequestTemplateContents: [
		"*Issue #, if available:*",
		"*Description of changes:*",
		"By submitting this pull request, I confirm that you can use, modify, copy, and redistribute this contribution, under the terms of your choice.",
	],
	defaultReleaseBranch: "main",
	name: "slack-bedrock-integration",
	projenrcTs: true,
	projenVersion: "0.85.2",
	deps: ["cdk-nag@2.28.185"],
	devDeps: ["license-checker@25.0.1", "repolinter@v0.11.2"],
	depsUpgrade: false,
	dependabot: true,
	dependabotOptions: {
		scheduleInterval: github.DependabotScheduleInterval.MONTHLY,
		ignoreProjen: false,
	},
	gitignore: ["*.dtmp", "*.bkp", ".env*", "!.env-sample", "aggregated_results.txt", "acat-output.json", "acat_report/*"],
	prettier: true,
	prettierOptions: {
		settings: {
			tabWidth: 4,
			useTabs: true,
			trailingComma: javascript.TrailingComma.ALL,
			printWidth: 140,
		},
	},
	eslintOptions: {
		prettier: true,
		dirs: ["src", "src/**", "test", "test/**"],
	},
});

const repolintWorkflow = project.github!.addWorkflow("repolint");
repolintWorkflow.on({
	pullRequest: {},
});
repolintWorkflow.addJob("repolint", {
	runsOn: ["ubuntu-24.04"],
	permissions: {
		contents: github.workflows.JobPermission.READ,
	},
	steps: [
		{
			name: "Checkout",
			uses: "actions/checkout@v4.2.0",
		},
		{
			name: "Lint",
			uses: "todogroup/repolinter-action@v1.7.1",
		},
	],
});

project.synth();
